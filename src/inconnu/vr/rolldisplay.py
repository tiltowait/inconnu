"""rolldisplay.py - A View for displaying roll outcomes and handling rerolls."""

import contextlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

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
    surge_reroll: bool = False  # Whether the surge's Rouse check rerolled a failure
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
        self.redacted_message: discord.Interaction | discord.WebhookMessage | None = None
        self.report_message: discord.Message | None = None
        self.public_message: discord.Message | None = None  # Guild rolls only
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
        if self.hide_dice:
            # Everyone sees the redacted roll. The roller privately gets the
            # full roll and the buttons.
            public = await self.ctx.respond(embed=self.redacted_embed)
            self.redacted_message = public
            self.message = await self.ctx.respond(embed=self.full_embed, view=self, ephemeral=True)
        else:
            public = await self.ctx.respond(embed=self.full_embed, view=self)
            self.message = public

        # Logging the message ID lets the roll be toggled for statistics
        # purposes. DM rolls aren't tracked, so they don't need it.
        message_id = None
        if self.ctx.guild is not None:
            self.public_message = await get_message(public)
            message_id = self.public_message.id
            if self.hide_dice:
                await self._report(self.public_message)
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
                ephemeral=self.hide_dice,
            )
            await services.post_update(
                ctx=interaction,
                character=self.character,
                title="Willpower Spent",
                message=f"**{self.character.name}** spent Willpower on a reroll.",
                msg=self.public_message,
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
        await self._update(interaction)
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
        self.state.surge_reroll = reroll
        await self._update(interaction)
        await inconnu.misc.perform_rouse(
            interaction, self.character, 1, "Surge", reroll, ephemeral=self.hide_dice
        )

    async def _report(self, public: discord.Message):
        """Send a hidden roll's full outcome to the update channel, if the
        guild has one, so the ST can see the dice."""
        self.report_message = await services.post_update(
            ctx=self.ctx,
            character=self.character,
            title="Hidden roll",
            message=f"Hidden roll: {public.jump_url}",
            embed=self.full_embed,
        )

    async def _update_copies(self):
        """Bring a hidden roll's public message and update channel report up to
        date. Either may have been deleted."""
        if self.redacted_message is not None:
            with contextlib.suppress(discord.NotFound):
                await self.redacted_message.edit(embed=self.redacted_embed)
        if self.report_message is not None:
            with contextlib.suppress(discord.NotFound, discord.Forbidden):
                await self.report_message.edit(embed=self.full_embed)

    async def _update(self, interaction: AppInteraction):
        """Redraw the buttons and embed, and bring the roll's copies up to date."""
        self._render_buttons()
        await interaction.response.edit_message(embed=self.full_embed, view=self)
        await self._update_copies()

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
            hidden=self.hide_dice,
        )

    # View hooks

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the roll's owner and the user who made the roll may press its
        buttons. They differ when an admin rolls for a player, and a hidden
        roll's buttons are only shown to the user who made it."""
        return interaction.user in (self.owner, self.ctx.user)

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
    def full_embed(self) -> discord.Embed:
        """An embed that shows the roll's entire outcome: total successes,
        margin, and the number of dice and their results."""
        return self._embed(hidden=False)

    @property
    def redacted_embed(self) -> discord.Embed:
        """An embed that shows only the roll's total successes and margin."""
        return self._embed(hidden=True)

    def _embed(self, hidden: bool) -> discord.Embed:
        """Build the embed, with or without the dice."""
        title = self.outcome.main_takeaway.upper() + "!"
        if not self.outcome.is_total_failure and not self.outcome.is_bestial:
            title += f" ({self.outcome.total_successes})"

        embed = discord.Embed(title=title, colour=self.outcome.embed_color)

        # Author line
        author_field = self.character_name
        if self.outcome.difficulty > 0:
            author_field += f" • DC {self.outcome.difficulty}"

        embed.set_author(name=author_field, icon_url=self.icon)
        embed.set_thumbnail(url=self.thumbnail_url)

        if hidden:
            embed.description = (
                f"**Margin:** {self.outcome.margin}\n**Difficulty:** {self.outcome.difficulty}"
            )
            # A number-only pool would reveal its size, and an Impairment
            # penalty would reveal the character's condition
            embed.add_field(name="Pool", value=self.readable_pool or "`Hidden`")
        else:
            self._add_dice_fields(embed)

        if updates := self.updates:
            embed.add_field(name="Updates", value=updates, inline=False)

        # Impairment notes would also reveal the character's condition
        footer = self._comment if hidden else self.comment
        if footer is not None:
            embed.set_footer(text=footer)

        return embed

    def _add_dice_fields(self, embed: discord.Embed):
        """Add the dice, pool size, Hunger, Difficulty, and pool string fields."""
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
        """The readable pool plus any impairment penalty. A penalized
        number-only pool shows its pre-penalty size."""
        penalty = None
        if self.outcome.impairment_penalty:
            impairment = self.outcome.impairment_penalty.description
            penalty = f"- {IMPAIRMENT_DICE} ({impairment} impairment)"

        pool_str = self.readable_pool
        if pool_str is None:
            return f"{self.outcome.base_pool} {penalty}" if penalty else None

        # Added after readable_pool's capitalization, which would otherwise
        # turn "(physical impairment)" into "(physical Impairment)"
        return f"{pool_str} {penalty}" if penalty else pool_str

    @property
    def readable_pool(self) -> str | None:
        """The pool string, made nicer to read, or None for number-only pools."""
        if not self.outcome.pool_str:
            return None

        splitted = de_camel(self.outcome.pool_str).split()

        # Uppercase each word in the pool. We can't use .title(), because
        # .title() will make everything else lowercase. "XYZ" would become
        # "Xyz", which is not desired.
        splitted = (t[0].upper() + t[1:] if t[0].islower() else t for t in splitted)
        return " ".join(splitted)

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
    def updates(self) -> str | None:
        """The roll's Surge, reroll, and Willpower status, one line each, if
        any apply. What hasn't been done yet is bolded."""
        lines = []
        if self.surging:
            if self.state.surge == _Surge.UNUSED:
                status = "**No Rouse**"
            elif self.state.surge_reroll:
                status = "Rouse Made w/ Re-roll"
            else:
                status = "Rouse Made"
            lines.append(f"`Surge:` {status}")

        if self.state.rerolled:
            lines.append(f"`Reroll:` {self.outcome.descriptor} from `{self.original_outcome}`")
            if self.character is not None:
                # Only characters have Willpower to mark
                lines.append("`WP:` Marked" if self.state.wp_marked else "`WP:` **Not Marked**")

        return "\n".join(lines) or None

    @property
    def surging(self) -> bool:
        """Whether the roll uses a Blood Surge."""
        if self.character is None or self.character.splat == "mortal":
            return False

        search = f"{self.outcome.pool_str} {self.comment}"
        return re.search(r"\bsurge\b", search, re.IGNORECASE) is not None
