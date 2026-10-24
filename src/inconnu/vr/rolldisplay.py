"""rolldisplay.py - A View for displaying roll outcomes and handling rerolls."""

import contextlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum, auto

import discord
from discord.ui import Button

import inconnu
import services
from ctx import AppInteraction
from inconnu.vr import dicemoji
from ui.views.reportingview import ReportingView
from utils import get_avatar, get_message
from utils.text import de_camel
from utils.urls import web_asset

PRIMARY = discord.ButtonStyle.primary
SECONDARY = discord.ButtonStyle.secondary
DANGER = discord.ButtonStyle.danger


class _Surge(Enum):
    """When the Blood Surge was used, if at all."""

    UNUSED = auto()
    BEFORE_REROLL = auto()
    AFTER_REROLL = auto()


@dataclass
class _ButtonState:
    """The owner's progress through the roll's buttons."""

    strategy: str | None = None
    wp_marked: bool = False
    surge: _Surge = _Surge.UNUSED
    timed_out: bool = False

    @property
    def rerolled(self) -> bool:
        """Whether a Willpower reroll has been made."""
        return self.strategy is not None


class RollDisplay(ReportingView):
    """Display and manipulate roll outcomes. Provides buttons for rerolls, WP, and Rouse."""

    def __init__(self, ctx, outcome, comment, character, owner, listener, timeout):
        super().__init__(timeout=600)
        self.ctx = ctx
        self.outcome = outcome
        self.original_outcome = f"{outcome.main_takeaway} ({outcome.total_successes})"
        self._comment = comment
        self.character = character
        self.owner = owner
        self.listener = listener
        self.timeout_handler = timeout
        self.state = _ButtonState()
        self.use_emoji = True  # Looked up when displayed

        self._render_buttons()

    async def display(self):
        """Send the roll."""
        self.use_emoji = await services.settings.can_emoji(self.ctx)
        inter = await self.ctx.respond(embed=self.embed, view=self)
        self.message = inter

        # Logging the message ID lets the roll be toggled for statistics
        # purposes. DM rolls aren't tracked, so they don't need it.
        message_id = None
        if self.ctx.guild is not None:
            message_id = (await get_message(inter)).id
        await self._log_roll(self.ctx, message_id)

    # Button actions

    async def reroll_failures(self, interaction: AppInteraction):
        """Re-roll up to three failing dice."""
        await self._reroll(interaction, "reroll_failures")

    async def maximize_criticals(self, interaction: AppInteraction):
        """Re-roll up to three non-critical dice."""
        await self._reroll(interaction, "maximize_criticals")

    async def avoid_messy(self, interaction: AppInteraction):
        """Re-roll up to three critical dice."""
        await self._reroll(interaction, "avoid_messy")

    async def risky_avoid_messy(self, interaction: AppInteraction):
        """Re-roll up to three critical dice plus failures."""
        await self._reroll(interaction, "risky")

    async def mark_wp(self, interaction: AppInteraction):
        """Mark Superficial Willpower damage for the reroll."""
        self.state.wp_marked = True
        await self._update(interaction)

        if self.character is not None:
            self.character.set_superficial_wp(self.character.superficial_wp + 1)
            await self.character.save()

            await inconnu.character.display(
                interaction,
                self.character,
                title="Willpower Spent",
                owner=self.owner,
                fields=[("New WP", inconnu.character.DisplayField.WILLPOWER)],
            )

    async def rouse(self, interaction: AppInteraction):
        """Make the surge's Rouse check."""
        await self._surge(interaction, False)

    async def rouse_with_reroll(self, interaction: AppInteraction):
        """Make the surge's Rouse check with a reroll."""
        await self._surge(interaction, True)

    async def _reroll(self, interaction: AppInteraction, strategy: str):
        """Reroll the outcome with the given strategy."""
        self.outcome.reroll(strategy)
        self.state.strategy = strategy
        await self._update(interaction, embed=self.embed)
        await self._log_roll(interaction, None)

        if self.listener:
            await self.listener(interaction, self.character, self.outcome)

    async def _surge(self, interaction: AppInteraction, reroll: bool):
        """Mark the surge as used and make the Rouse check."""
        if self.state.rerolled:
            self.state.surge = _Surge.AFTER_REROLL
        else:
            self.state.surge = _Surge.BEFORE_REROLL
        await self._update(interaction)
        await inconnu.misc.rouse(interaction, self.character, 1, "Surge", reroll)

    async def _update(self, interaction: AppInteraction, **kwargs):
        """Redraw the buttons and edit the message."""
        self._render_buttons()
        await interaction.response.edit_message(view=self, **kwargs)

    async def _log_roll(self, source, message_id: int | None):
        """Log the roll for statistics. Rerolls are logged without a message ID."""
        guild_id = source.guild.id if source.guild is not None else None
        channel_id = source.channel.id if source.guild is not None else None

        await inconnu.stats.log_roll(
            guild_id,
            channel_id,
            self.owner.id,
            message_id,
            self.character,
            self.outcome,
            self.comment,
        )

    # View hooks

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the roll's owner may press its buttons."""
        return interaction.user == self.owner

    async def on_check_failure(self, interaction: discord.Interaction):
        """Tell the presser the buttons aren't theirs."""
        await interaction.response.send_message(
            "This button doesn't belong to you!", ephemeral=True
        )

    async def on_timeout(self):
        """Disable the buttons and inform the timeout handler."""
        self.state.timed_out = True
        self._render_buttons()

        if self.message is not None:
            with contextlib.suppress(discord.NotFound):
                await self.message.edit(view=self)

        if self.timeout_handler is not None:
            await self.timeout_handler(self.outcome)

    # Buttons

    def _render_buttons(self):
        """Rebuild the buttons from the current state."""
        self.clear_items()
        for button in self._buttons():
            if self.state.timed_out:
                button.disabled = True
            self.add_item(button)

        if all(child.disabled for child in self.children):  # type: ignore[attr-defined]
            # Nothing can be pressed, so we don't need to listen
            self.stop()

    def _buttons(self) -> list[Button]:
        """The buttons for the current state."""
        if not self.state.rerolled:
            buttons = self._reroll_buttons()
            if self.surging:
                used = self.state.surge != _Surge.UNUSED
                buttons.extend(self._surge_buttons(used, row=1))
            return buttons

        if self.character is None:
            # Without a character, there's nothing to do after a reroll
            return self._reroll_buttons()

        marked = self.state.wp_marked
        buttons = [
            self._button("Mark WP Use", SECONDARY if marked else PRIMARY, marked, self.mark_wp)
        ]
        if self.surging and self.state.surge != _Surge.BEFORE_REROLL:
            used = self.state.surge == _Surge.AFTER_REROLL
            buttons.extend(self._surge_buttons(used))
        return buttons

    def _reroll_buttons(self) -> list[Button]:
        """The Willpower reroll buttons. After a reroll, they're all disabled."""
        if not self.outcome.can_reroll:
            # They don't have any Attributes in their pool. This will only show
            # if they used a Trait in the roll. If they just used numbers, then
            # they will always get re-roll buttons.
            #
            # Examples: Resolve + Composure: WP NOT allowed.
            #           Strength + Brawl: WP allowed.
            return [self._button("WP Unavailable (p.158)", SECONDARY, True)]

        strategies = [
            (
                "Re-Roll Failures",
                "reroll_failures",
                self.outcome.can_reroll_failures,
                self.reroll_failures,
            ),
            (
                "Max Crits",
                "maximize_criticals",
                self.outcome.can_maximize_criticals,
                self.maximize_criticals,
            ),
            (
                "Avoid Messy",
                "avoid_messy",
                self.outcome.can_avoid_messy_critical,
                self.avoid_messy,
            ),
            (
                "Risky Avoid",
                "risky",
                self.outcome.can_risky_messy_critical,
                self.risky_avoid_messy,
            ),
        ]

        buttons = []
        for label, strategy, available, callback in strategies:
            if self.state.rerolled:
                style = SECONDARY if strategy == self.state.strategy else PRIMARY
                buttons.append(self._button(label, style, True, callback))
            else:
                buttons.append(self._button(label, PRIMARY, not available, callback))
        return buttons

    def _surge_buttons(self, used: bool, row: int | None = None) -> list[Button]:
        """The Rouse buttons for a Blood Surge."""
        style = SECONDARY if used else DANGER
        return [
            self._button("Rouse", style, used, self.rouse, row),
            self._button("Rouse w/ Reroll", style, used, self.rouse_with_reroll, row),
        ]

    @staticmethod
    def _button(
        label: str,
        style: discord.ButtonStyle,
        disabled: bool,
        callback: Callable[[AppInteraction], Awaitable[None]] | None = None,
        row: int | None = None,
    ) -> Button:
        """Create a button with the given callback."""
        button = Button(label=label, style=style, disabled=disabled, row=row)
        if callback is not None:
            button.callback = callback  # type: ignore[method-assign]
        return button

    # Embed

    @property
    def embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.outcome.main_takeaway.upper() + "!"
        if self.state.rerolled:
            title = f"R: {title}"
        if not self.outcome.is_total_failure and not self.outcome.is_bestial:
            title += f" ({self.outcome.total_successes})"

        embed = discord.Embed(title=title, colour=self.outcome.embed_color)

        # Author line
        author_field = self.character_name
        if self.outcome.difficulty > 0:
            author_field += f" • DC {self.outcome.difficulty}"
        if self.outcome.descriptor is not None:
            author_field += f" • {self.outcome.descriptor}"

        embed.set_author(name=author_field, icon_url=self.icon)
        embed.set_thumbnail(url=self.thumbnail_url)

        # Disclosure fields
        if self.outcome.pool <= 30 and self.use_emoji:
            normalmoji = dicemoji.emojify(self.outcome.normal.dice, False)
            hungermoji = dicemoji.emojify(self.outcome.hunger.dice, True)
            embed.add_field(
                name=f"Margin: {self.outcome.margin}",
                value=f"{normalmoji} {hungermoji}",
                inline=False,
            )
        else:
            lines = []
            if self.outcome.normal.count > 0:
                dice = sorted(self.outcome.normal.dice, reverse=True)
                lines.append("**Normal Dice:** " + ", ".join(map(str, dice)))
            if self.outcome.hunger.count > 0:
                dice = sorted(self.outcome.hunger.dice, reverse=True)
                lines.append("**Hunger Dice:** " + ", ".join(map(str, dice)))
            else:
                lines.append("**Hunger:** None")

            embed.add_field(
                name=f"Margin: {self.outcome.margin}", value="\n".join(lines), inline=False
            )

        embed.add_field(name="Dice", value=str(self.outcome.pool))
        embed.add_field(name="Hunger", value=str(self.hunger))
        embed.add_field(name="Difficulty", value=str(self.outcome.difficulty))

        if self.outcome.pool_str:
            embed.add_field(name="Pool", value=self.pool_str)

        # Show what the roll originally was
        if self.state.rerolled:
            embed.add_field(
                name="Original Outcome",
                value=f"```{self.original_outcome}```",
                inline=False,
            )

        if self.comment is not None:
            embed.set_footer(text=self.comment)

        return embed

    @property
    def character_name(self) -> str:
        """The character's display name. Either the character name or the player name."""
        if self.character is not None:
            return self.character.name
        return self.owner.display_name

    @property
    def hunger(self) -> str | int:
        """
        The Hunger for the roll. This uses the character's Hunger if possible and
        falls back to the hunger dice count if unavailable.
        """
        if self.character is not None:
            if self.character.is_vampire:
                if self.character.hunger == 0 and self.outcome.hunger.count == 0:
                    # Vampires are rarely at Hunger 0, so it can raise a few
                    # eyebrows when STs see a 0 here. Often, it means the player
                    # forgot to input Hunger. Saying "sated" when Hunger is
                    # actually 0 helps to assure onlookers that a Hunger rating of
                    # zero is correct.
                    return "*Sated*"
                elif self.character.hunger == self.outcome.hunger_rating:
                    return f"{self.outcome.hunger_rating} (Current)"
            else:
                return "*Mortal*"

        # We were given a specific Hunger (or implicit 0), a character wasn't
        # given, or possibly both.
        return self.outcome.hunger_rating

    @property
    def pool_str(self) -> str:
        """The pool string, made nicer to read."""
        splitted = de_camel(self.outcome.pool_str).split()

        # Uppercase each word in the pool. We can't use .title(), because
        # .title() will make everything else lowercase. "XYZ" would become
        # "Xyz", which is not desired.
        splitted = (t[0].upper() + t[1:] if t[0].islower() else t for t in splitted)
        return " ".join(splitted)

    @property
    def comment(self):
        """The original comment, plus any impairment string."""
        if self.character is not None:
            if (impairment := self.character.impairment) is not None:
                comment = (self._comment + "\n") if self._comment else ""
                return comment + impairment
        return self._comment

    @property
    def icon(self):
        """The icon for the embed."""
        if self.character is not None and not self.character.is_pc:
            return self.ctx.guild.icon or ""
        return get_avatar(self.owner)

    @property
    def thumbnail_url(self) -> str:
        """The URL for the embed thumbnail."""
        if self.outcome.is_critical:
            return web_asset("dice/crit.webp")
        if self.outcome.is_messy:
            return web_asset("dice/messy.webp")
        if self.outcome.is_successful:
            return web_asset("dice/success.webp")
        if self.outcome.is_failure:
            return web_asset("dice/fail.webp")
        if self.outcome.is_total_failure:
            return web_asset("dice/total-fail.webp")

        return web_asset("dice/bestial.webp")

    @property
    def surging(self) -> bool:
        """Whether the roll uses a Blood Surge."""
        if self.character is None or self.character.splat == "mortal":
            return False

        search = f"{self.outcome.pool_str} {self.comment}"
        return re.search(r"\bsurge\b", search, re.IGNORECASE) is not None
