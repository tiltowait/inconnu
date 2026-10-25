"""rolldisplay.py - A View for displaying roll outcomes and handling rerolls."""

import contextlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, cast

import discord
from discord.ui import Button

import inconnu
import services
from ctx import AppCtx, AppInteraction, AppInvocation
from inconnu.character.impairment import impairment_reminder, incapacitation_reminder
from inconnu.roll import Roll, Strategy
from inconnu.vr import dicemoji
from models import IMPAIRMENT_DICE, ImpairmentCategory, RollCategory, VChar
from ui.views.reportingview import ReportingView
from utils import get_avatar, get_message
from utils.text import de_camel
from utils.urls import web_asset

type RerollListener = Callable[[AppInteraction, VChar | None, Roll], Awaitable[None]]
type TimeoutHandler = Callable[[Roll], Awaitable[None]]

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

    strategy: Strategy | None = None
    wp_marked: bool = False
    surge: _Surge = _Surge.UNUSED
    timed_out: bool = False

    @property
    def rerolled(self) -> bool:
        """Whether a Willpower reroll has been made."""
        return self.strategy is not None


class RollDisplay(ReportingView):
    """Display and manipulate roll outcomes. Provides buttons for rerolls, WP, and Rouse."""

    def __init__(
        self,
        ctx: AppCtx,
        outcome: Roll,
        comment: str | None,
        character: VChar | None,
        owner: discord.Member | discord.User,
        listener: RerollListener | None,
        timeout: TimeoutHandler | None,
        *,
        impairment_category: ImpairmentCategory | None = None,
        hide_dice=False,
    ):
        super().__init__(timeout=600)
        self.ctx = ctx
        self.outcome = outcome
        self.original_outcome = f"{outcome.main_takeaway} ({outcome.total_successes})"
        self._comment = comment
        self.character = character
        self.owner = owner
        self.listener = listener
        self.timeout_handler = timeout
        self.impairment_category = impairment_category
        self.hide_dice = hide_dice
        self.state = _ButtonState()
        self.use_emoji = True  # Looked up when displayed
        self.auto_impairment = False  # Looked up when displayed

        self._render_buttons()

    async def display(self):
        """Send the roll."""
        self.use_emoji = await services.settings.can_emoji(self.ctx)
        if self.character is not None:
            # Only needed to word the Impairment reminder, which requires a character
            self.auto_impairment = await services.settings.auto_impairment(self.ctx)
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
        await self._reroll(interaction, Strategy.REROLL_FAILURES)

    async def maximize_criticals(self, interaction: AppInteraction):
        """Re-roll up to three non-critical dice."""
        await self._reroll(interaction, Strategy.MAXIMIZE_CRITICALS)

    async def avoid_messy(self, interaction: AppInteraction):
        """Re-roll up to three critical dice."""
        await self._reroll(interaction, Strategy.AVOID_MESSY)

    async def risky_avoid_messy(self, interaction: AppInteraction):
        """Re-roll up to three critical dice plus failures."""
        await self._reroll(interaction, Strategy.RISKY)

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
                owner=cast(discord.Member, self.owner),  # Characters only exist in guilds
                fields=[("New WP", inconnu.character.DisplayField.WILLPOWER)],
            )

    async def rouse(self, interaction: AppInteraction):
        """Make the surge's Rouse check."""
        await self._surge(interaction, False)

    async def rouse_with_reroll(self, interaction: AppInteraction):
        """Make the surge's Rouse check, rolling two dice and keeping the higher."""
        await self._surge(interaction, True)

    async def _reroll(self, interaction: AppInteraction, strategy: Strategy):
        """Reroll the outcome with the given strategy."""
        self.outcome.reroll(strategy.value)
        self.state.strategy = strategy
        await self._update(interaction, embed=self.embed)
        await self._log_roll(interaction, None)

        if self.listener:
            await self.listener(interaction, self.character, self.outcome)

    async def _surge(self, interaction: AppInteraction, reroll: bool):
        """Mark the surge as used and make the Rouse check."""
        if self.character is None:
            # Surge buttons only appear for characters
            return

        if self.state.rerolled:
            self.state.surge = _Surge.AFTER_REROLL
        else:
            self.state.surge = _Surge.BEFORE_REROLL
        await self._update(interaction)
        await inconnu.misc.rouse(interaction, self.character, 1, "Surge", reroll)

    async def _update(self, interaction: AppInteraction, **kwargs: Any):
        """Redraw the buttons and edit the message."""
        self._render_buttons()
        await interaction.response.edit_message(view=self, **kwargs)

    async def _log_roll(self, source: AppInvocation, message_id: int | None):
        """Log the roll for statistics. Rerolls are logged without a message ID."""
        if source.guild is not None and source.channel is not None:
            guild_id, channel_id = source.guild.id, source.channel.id
        else:
            guild_id = channel_id = None

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
            # None of the supplied Traits are Attributes. (This never fires if
            # no Traits are given.)
            return [self._button("WP Unavailable (p.158)", SECONDARY, True)]

        strategies = [
            (
                "Re-Roll Failures",
                Strategy.REROLL_FAILURES,
                self.outcome.can_reroll_failures,
                self.reroll_failures,
            ),
            (
                "Max Crits",
                Strategy.MAXIMIZE_CRITICALS,
                self.outcome.can_maximize_criticals,
                self.maximize_criticals,
            ),
            (
                "Avoid Messy",
                Strategy.AVOID_MESSY,
                self.outcome.can_avoid_messy_critical,
                self.avoid_messy,
            ),
            (
                "Risky Avoid",
                Strategy.RISKY,
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
        embed.add_field(name="Hunger", value=self.hunger)
        embed.add_field(name="Difficulty", value=str(self.outcome.difficulty))

        if pool_str := self.pool_str:
            embed.add_field(name="Pool", value=pool_str)

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
    def hunger(self) -> str:
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
        return str(self.outcome.hunger_rating)

    @property
    def pool_str(self) -> str | None:
        """The pool string, made nicer to read, plus any impairment penalty. A
        penalized number-only pool shows its pre-penalty size."""
        penalty = None
        if self.outcome.impairment_penalty:
            impairment = self.outcome.impairment_penalty.description
            penalty = f"- {IMPAIRMENT_DICE} ({impairment} impairment)"

        if not self.outcome.pool_str:
            return f"{self.outcome.base_pool} {penalty}" if penalty else None

        splitted = de_camel(self.outcome.pool_str).split()

        # Uppercase each word in the pool. We can't use .title(), because
        # .title() will make everything else lowercase. "XYZ" would become
        # "Xyz", which is not desired.
        splitted = (t[0].upper() + t[1:] if t[0].islower() else t for t in splitted)
        pool_str = " ".join(splitted)

        # Added after the capitalization above, which would otherwise turn
        # "(physical impairment)" into "(physical Impairment)"
        if penalty is not None:
            pool_str += f" {penalty}"

        return pool_str

    @property
    def comment(self) -> str | None:
        """The original comment, plus any impairment note."""
        if self.impairment_note is not None:
            comment = (self._comment + "\n") if self._comment else ""
            return comment + self.impairment_note
        return self._comment

    @property
    def impairment_note(self) -> str | None:
        """
        The Impairment line for the comment, if any, in order of priority:

        1. Torpor or death
        2. An override notice, if the user's Impairment category changed whether
           the character's Impairment applies to this roll
        3. Nothing, if the penalty was applied (it's shown in the Pool field)
        4. A reminder, if the character is impaired, worded for the user's
           auto-impairment setting so auto users aren't told to subtract dice
        """
        if self.character is None:
            return None
        if self.character.incapacitated:
            return incapacitation_reminder(self.character)
        override = self.impairment_override
        if override is ImpairmentCategory.IGNORE:
            return "Override: Impairment ignored"
        if override is not None:
            return f"Override: {override.label} roll"
        if self.outcome.impairment_penalty:
            return None

        return impairment_reminder(self.character, automatic=self.auto_impairment)

    @property
    def impairment_override(self) -> ImpairmentCategory | None:
        """The user's Impairment category, if it changed whether the character's
        Impairment applies to this roll. The user's setting doesn't factor in."""
        if self.character is None or self.impairment_category is None:
            return None

        impairment = self.character.impairment_state
        detected = impairment.penalizes(RollCategory.from_pool(self.outcome.pool_str))
        chosen = impairment.penalizes(self.impairment_category.roll_category)
        return self.impairment_category if detected != chosen else None

    @property
    def icon(self) -> str | discord.Asset:
        """
        The embed author's icon. Normally, this is the roller's avatar.

        SPCs are owned by the bot rather than a player, so showing the avatar
        of whichever Storyteller rolled for one would be misleading. Instead,
        SPC rolls use the guild's icon (or no icon, if the guild doesn't have
        one). SPCs only exist in guilds; the guild check is for the type
        checker.

        Character profile images aren't used, because they're unreadable at
        author-icon size.
        """
        if self.character is not None and not self.character.is_pc and self.ctx.guild is not None:
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
