"""rolldisplay.py - A class for managing the display of roll outcomes and rerolls."""
# pylint: disable=too-many-arguments, too-many-instance-attributes

import asyncio
import random
import re

import discord
from discord_ui import Listener
from discord_ui.components import Button

from . import dicemoji
from .. import character as char
from .. import stats
from .dicethrow import DiceThrow
from ..misc import rouse
from ..vchar import contains_digit

__MAX_REROLL = 3


class RollDisplay(Listener):
    """Display and manipulate roll outcomes. Provides buttons for rerolls, wp, and rouse."""

    _REROLL_FAILURES = "reroll_failures"
    _MAXIMIZE_CRITICALS = "maximize_criticals"
    _AVOID_MESSY = "avoid_messy"
    _RISKY_AVOID_MESSY = "risky"
    _WILLPOWER = "willpower"


    def __init__(self, ctx, outcome, comment, character, owner):
        self.ctx = ctx
        self.outcome = outcome
        self.comment = comment
        self.character = character
        self.owner = owner
        self.rerolled = False
        self.surged = False
        self.msg = None # This is used for disabling the buttons at the end of the timeout

        # Add impairment to the comment, if necessary
        if character is not None:
            impairment = self.character.impairment
            if impairment is not None:
                if self.comment is not None:
                    if impairment not in self.comment:
                        self.comment += f"\n{impairment}"
                else:
                    self.comment = impairment

        super().__init__(timeout=60)


    def _stop(self):
        """Stop the listener and disable the buttons."""
        super()._stop()
        asyncio.create_task(self.msg.disable_components())


    async def display(self, use_embed: bool, alt_ctx=None):
        """Display the roll."""

        # Log the roll. Doing it here captures normal rolls, re-rolls, and macros
        if self.ctx.guild is not None:
            stats.Stats.log_roll(self.ctx.guild.id, self.owner.id,
                self.character, self.outcome, self.comment
            )
        else:
            stats.Stats.log_roll(None, self.owner.id, self.character, self.outcome, self.comment)

        # We might be responding to a button
        ctx = alt_ctx or self.ctx

        if use_embed:
            msg = await ctx.respond(embed=self.embed, components=self.buttons)
        else:
            msg = await ctx.respond(self.text, components=self.buttons)

        # In order to avoid errors, we spawn a new listener in the case of a reroll
        if alt_ctx:
            alt = RollDisplay(ctx, self.outcome, self.character, self.comment, self.owner)
            alt.attach_me_to(msg)
            alt.msg = msg
        else:
            self.attach_me_to(msg)
            self.msg = msg


    @Listener.button()
    async def respond_to_button(self, btn):
        """Respond to the buttons."""
        if btn.author.id != self.ctx.author.id:
            await btn.respond("This button doesn't belong to you!", hidden=True)
            return

        if btn.custom_id == self._WILLPOWER:
            if self.character is not None:
                self.character.superficial_wp += 1

            await char.display(btn, self.character,
                title="Willpower Spent",
                owner=self.owner,
                fields=[("New WP", char.WILLPOWER)]
            )
            await btn.message.disable_components(index=0)

        elif contains_digit(btn.custom_id): # Surge buttons are just charids
            self.surged = True
            await rouse(btn, 1, self.character, "Surge", False)

            # The surge button is always the last button
            index = len(btn.message.components) - 1
            await btn.message.disable_components(index=index)

        else:
            # We're rerolling
            strategy = btn.custom_id
            self.outcome = self.reroll(strategy)
            self.rerolled = True

            # Determine whether to display an embed or not
            use_embed = len(btn.message.embeds) > 0
            await self.display(use_embed, btn)
            await btn.message.disable_components()


    @property
    def character_name(self) -> str:
        """The character's display name. Either the character name or the player name."""
        if self.character is not None:
            character_name = self.character.name
        else:
            character_name = self.owner.display_name

        return character_name


    @property
    def icon(self) -> str:
        """The icon for the embed."""
        if self.character is not None:
            guild_icon = self.ctx.guild.icon or ""
            icon = self.owner.display_avatar if self.character.is_pc else guild_icon
        else:
            icon = self.owner.display_avatar

        return icon


    @property
    def embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.outcome.main_takeaway
        if not self.outcome.is_total_failure and not self.outcome.is_bestial:
            title += f" ({self.outcome.total_successes})"

        embed = discord.Embed(
            title=title,
            colour=self.outcome.embed_color
        )

        # Author line
        author_field = self.character_name + ("'s reroll" if self.rerolled else "'s roll")
        if self.outcome.difficulty > 0:
            author_field += f" vs diff. {self.outcome.difficulty}"
        if self.outcome.descriptor is not None:
            author_field += f" ({self.outcome.descriptor})"

        embed.set_author(
            name=author_field,
            icon_url=self.icon
        )

        # Disclosure fields
        if self.outcome.dice_count < 35:
            normalmoji = dicemoji.emojify(self.outcome.normal.dice, False)
            hungermoji = dicemoji.emojify(self.outcome.hunger.dice, True)
            embed.add_field(
                name=f"Margin: {self.outcome.margin}",
                value=f"{normalmoji} {hungermoji}",
                inline=False
            )
        else:
            lines = []
            if self.outcome.normal.count > 0:
                dice = sorted(self.outcome.normal.dice, reverse=True)
                lines.append("**Normal Dice:** " + ", ".join(map(str, dice)))
            if self.outcome.hunger.count > 0:
                dice = sorted(self.outcome.hunger.dice, reverse=True)
                lines.append("**Hunger Dice:** " + ", ".join(map(str, dice)))

            embed.add_field(
                name=f"Margin: {self.outcome.margin}",
                value="\n".join(lines),
                inline=False
            )

        embed.add_field(name="Pool", value=str(self.outcome.pool))
        embed.add_field(name="Hunger", value=str(self.outcome.hunger.count))
        embed.add_field(name="Difficulty", value=str(self.outcome.difficulty))

        if self.outcome.pool_str is not None:
            embed.add_field(name="Pool", value=self.outcome.pool_str)

        if self.comment is not None:
            embed.set_footer(text=self.comment)

        return embed


    @property
    def text(self) -> str:
        """The textual representation of the roll."""

        # Determine the name for the "author" field
        if self.character is not None:
            title = self.character.name
        else:
            title = self.owner.display_name

        title += "'s reroll" if self.rerolled else "'s roll"
        if self.outcome.difficulty > 0:
            title += f" vs diff. {self.outcome.difficulty}"
        if self.outcome.descriptor is not None:
            title += f" ({self.outcome.descriptor})"

        contents = [f"```{title}```"]

        takeaway = self.outcome.main_takeaway
        if not self.outcome.is_total_failure and not self.outcome.is_bestial:
            takeaway += f" ({self.outcome.total_successes})"

        contents.append(takeaway)
        contents.append(f"Margin: `{self.outcome.margin}`")
        contents.append(f"Normal: `{', '.join(map(str, self.outcome.normal.dice))}`")
        if len(self.outcome.hunger.dice) > 0:
            contents.append(f"Hunger: `{', '.join(map(str, self.outcome.hunger.dice))}`")

        if self.outcome.pool_str is not None:
            contents.append(f"Pool: `{self.outcome.pool_str}`")

        if self.comment is not None:
            contents.append(f"```{self.comment}```")

        return "\n".join(contents)


    @property
    def surging(self) -> bool:
        """Whether the roll uses a Blood Surge."""
        search = f"{self.outcome.pool_str} {self.comment}"
        match = re.match(r"^.*(\s+surge|surge\s+.*|surge)$", search, re.IGNORECASE)
        return match is not None


    @property
    def buttons(self) -> list:
        """Generate the buttons for Willpower re-rolls and surging."""
        buttons = []

        if self.rerolled:
            if self.character is not None:
                buttons.append(Button("Mark WP", self._WILLPOWER))
                if self.surging:
                    buttons.append(Button("Rouse", str(self.character.id), "red"))
            return buttons if len(buttons) > 0 else None

        # We haven't re-rolled

        if self.outcome.can_reroll_failures:
            buttons.append(Button("Re-Roll Failures", self._REROLL_FAILURES))

        if self.outcome.can_maximize_criticals:
            buttons.append(Button("Maximize Crits", self._MAXIMIZE_CRITICALS))

        if self.outcome.can_avoid_messy_critical:
            buttons.append(Button("Avoid Messy", self._AVOID_MESSY))

        if self.outcome.can_risky_messy_critical:
            buttons.append(Button("Risky Avoid Messy", self._RISKY_AVOID_MESSY))

        if self.surging:
            buttons.append(Button("Rouse", str(self.character.id), "red"))

        return buttons if len(buttons) > 0 else None


    def reroll(self, strategy):
        """Perform a reroll based on a given strategy."""
        new_dice = None
        descriptor = None

        rerolled = self.outcome

        if strategy == "reroll_failures":
            new_dice = _reroll_failures(self.outcome.normal.dice)
            rerolled.strategy = "failures"
            descriptor = "Rerolling Failures"

        elif strategy == "maximize_criticals":
            new_dice = _maximize_criticals(self.outcome.normal.dice)
            rerolled.strategy = "criticals"
            descriptor = "Maximizing Criticals"

        elif strategy == "avoid_messy":
            new_dice = _avoid_messy(self.outcome.normal.dice)
            rerolled.strategy = "messy"
            descriptor = "Avoiding Messy Critical"

        elif strategy == "risky":
            new_dice = _risky_avoid_messy(self.outcome.normal.dice)
            rerolled.strategy = "risky"
            descriptor = "Avoid Messy (Risky)"

        new_throw = DiceThrow(new_dice)
        rerolled.normal = new_throw
        rerolled.descriptor = descriptor

        return rerolled


def _reroll_failures(dice: list) -> list:
    """Re-roll up to three failing dice."""
    new_dice = []
    rerolled = 0

    for die in dice:
        if die >= 6 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def _maximize_criticals(dice: list) -> list:
    """Re-roll up to three non-critical dice."""

    # If there are 3 or more failure dice, we don't need to re-roll any successes.
    # To avoid accidentally skipping a die that needs to be re-rolled, we will
    # convert successful dice until our total failures equals 3

    # Technically, we could do this in two passes: re-roll failures, then re-
    # roll non-criticals until we hit 3 re-rolls. It would certainly be the more
    # elegant solution. However, that method would frequently result in the same
    # die being re-rolled twice. This isn't technically against RAW, but it's
    # against the spirit and furthermore increases the likelihood of bug reports
    # due to people seeing dice frequently not being re-rolled when they expect
    # them to be.

    # Thus, we use this ugly method.
    total_failures = len(list(filter(lambda die: die < 6, dice)))
    if total_failures < __MAX_REROLL:
        for index, die in enumerate(dice):
            if 6 <= die < 10: # Non-critical success
                dice[index] = 1
                total_failures += 1

                if total_failures == __MAX_REROLL:
                    break

    # We have as many re-rollable dice as we can
    new_dice = []
    rerolled = 0

    for die in dice:
        if die >= 6 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def _avoid_messy(dice: list) -> list:
    """Re-roll up to three critical dice."""
    new_dice = []
    rerolled = 0

    for die in dice:
        if die != 10 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def _risky_avoid_messy(dice: list) -> list:
    """Re-roll up to three critical dice plus one or two failing dice."""
    new_dice = []
    tens_remaining = dice.count(10)
    fails_remaining = 3 - tens_remaining

    for die in dice:
        if tens_remaining > 0 and die == 10:
            new_dice.append(__d10())
            tens_remaining -= 1
        elif die < 6 and fails_remaining > 0:
            new_dice.append(__d10())
            fails_remaining -= 1
        else:
            new_dice.append(die)

    return new_dice


def __d10() -> int:
    """Roll a d10."""
    return random.randint(1, 10)
