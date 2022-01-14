"""rolldisplay.py - A class for managing the display of roll outcomes and rerolls."""
# pylint: disable=too-many-arguments, too-many-instance-attributes

import asyncio
import re

import discord
from discord_ui import Listener
from discord_ui.components import Button

from . import dicemoji
from .. import character as char
from .. import stats
from ..misc import rouse
from ..vchar import contains_digit


class RollDisplay(Listener):
    """Display and manipulate roll outcomes. Provides buttons for rerolls, wp, and rouse."""

    _REROLL_FAILURES = "reroll_failures"
    _MAXIMIZE_CRITICALS = "maximize_criticals"
    _AVOID_MESSY = "avoid_messy"
    _RISKY_AVOID_MESSY = "risky"
    _WILLPOWER = "willpower"


    def __init__(self, ctx, outcome, comment, character, owner):
        super().__init__(timeout=600)

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


    def _stop(self):
        """Stop the listener and disable the buttons."""
        super()._stop()

        if len(self.message.components) > 0 :
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

        # A listener can only listen to one message at a time, so we need a second
        # one for the new message. It won't display data, so it doesn't need any
        # of the state variables, only the user/character data.
        if alt_ctx:
            alt = RollDisplay(ctx, self.outcome, self.comment, self.character, self.owner)
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
            self.outcome.reroll(strategy)
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
    def thumbnail_url(self) -> str:
        """The URL for the embed thumbnail."""
        if self.outcome.is_critical:
            return "https://www.inconnu-bot.com/images/assets/dice/crit.webp"
        if self.outcome.is_messy:
            return "https://www.inconnu-bot.com/images/assets/dice/messy.webp"
        if self.outcome.is_successful:
            return "https://www.inconnu-bot.com/images/assets/dice/success.webp"
        if self.outcome.is_failure:
            return "https://www.inconnu-bot.com/images/assets/dice/fail.webp"
        if self.outcome.is_total_failure:
            return "https://www.inconnu-bot.com/images/assets/dice/total-fail.webp"

        return "https://www.inconnu-bot.com/images/assets/dice/bestial.webp"


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
        embed.set_thumbnail(url=self.thumbnail_url)

        # Disclosure fields
        if self.outcome.pool < 35:
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
        if self.character is None or self.character.splat == "mortal":
            return False

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
                if not self.surged and self.surging:
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
