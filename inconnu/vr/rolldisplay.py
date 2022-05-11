"""rolldisplay.py - A class for managing the display of roll outcomes and rerolls."""
# pylint: disable=too-many-arguments, too-many-instance-attributes

import asyncio
import re
import uuid
from enum import Enum

import discord
from discord.ui import Button

import inconnu

from . import dicemoji


class _ButtonID(str, Enum):
    """Button IDs used in re-rolls."""

    REROLL_FAILURES = "reroll_failures"
    MAXIMIZE_CRITICALS = "maximize_criticals"
    AVOID_MESSY = "avoid_messy"
    RISKY_AVOID_MESSY = "risky"
    WILLPOWER = "willpower"

    def unique(self):
        """Return the string value of the case, uniquely identified."""
        return f"{self} {uuid.uuid4()}"


class _RollControls(inconnu.views.DisablingView):
    """A View that has a dynamic number of roll buttons."""

    def __init__(self, has_character, callback, owner, buttons):
        super().__init__(timeout=600)
        self.has_character = has_character
        self.callback = callback
        self.owner = owner

        for button in buttons:
            button.callback = self.button_pressed
            self.add_item(button)

    async def button_pressed(self, interaction):
        """Handle button presses."""
        if self.owner != interaction.user:
            await interaction.response.send_message(
                "This button doesn't belong to you!", ephemeral=True
            )
        else:
            button_id = interaction.data["custom_id"].split()[0]  # Remove the unique ID

            if inconnu.common.contains_digit(button_id):
                # This was the surge button, which is always last. Let's disable it
                self.children[-1].disabled = True
                self.children[-1].style = discord.ButtonStyle.secondary
                await interaction.response.edit_message(view=self)
            elif button_id == _ButtonID.WILLPOWER:
                # Mark WP is always the first button
                self.children[0].disabled = True
                self.children[0].style = discord.ButtonStyle.secondary
                await interaction.response.edit_message(view=self)
            else:
                if not self.has_character:
                    # Find the pressed button and make it gray
                    for child in self.children:
                        # We need the full custom id here, not just the button ID
                        if child.custom_id == interaction.data["custom_id"]:
                            child.style = discord.ButtonStyle.secondary
                    await self.disable_items(interaction)
                else:
                    self.stop()

            await self.callback(interaction)


class RollDisplay:
    """Display and manipulate roll outcomes. Provides buttons for rerolls, wp, and rouse."""

    def __init__(self, ctx, outcome, comment, character, owner):
        self.ctx = ctx
        self.outcome = outcome
        self.original_outcome = f"{outcome.main_takeaway} ({outcome.total_successes})"
        self._comment = comment
        self.character = character
        self.owner = owner
        self.rerolled = False
        self.surged = False
        self.msg = None  # Used for disabling the buttons at the end of the timeout
        self.controls = None

    async def display(self, alt_ctx=None):
        """Display the roll."""
        # We might be responding to a button
        ctx = alt_ctx or self.ctx
        msg_contents = {}

        if buttons := self.buttons:
            self.controls = _RollControls(
                self.character is not None, self.respond_to_button, self.owner, buttons
            )
            msg_contents["view"] = self.controls

        msg_contents["embed"] = await self.get_embed()

        if not self.rerolled:
            inter = await inconnu.respond(ctx)(**msg_contents)
        else:
            # We need this if statement, because if there *is* a character, we
            # don't waste time disabling the buttons, because we're just going
            # to overwrite them with a new view. Unfortunately, we need to use
            # a different method call in this instance, and we *also* need to
            # acquire the inter object differently.
            if self.character is not None:
                # Interaction is not a followup
                await ctx.response.edit_message(**msg_contents)
                inter = ctx
            else:
                # The interaction is a followup
                inter = await ctx.edit_original_message(**msg_contents)

        if self.controls is not None:
            # Attach the interaction so we can disable the buttons when appropriate
            self.controls.message = inter

        # Log the roll. Doing it here captures normal rolls, re-rolls, and
        # macros. We get the roll's message ID so we can toggle the message
        # for statistics purposes.

        if ctx.guild is not None:
            if not self.rerolled:
                msg = await inconnu.get_message(inter)
                msg_id = msg.id
            else:
                msg_id = None

            await inconnu.stats.log_roll(
                ctx.guild.id, self.owner.id, msg_id, self.character, self.outcome, self.comment
            )
        else:
            # If this is a DM roll, we don't keep stats, so we don't need to
            # get the message ID
            await inconnu.stats.log_roll(
                None, self.owner.id, None, self.character, self.outcome, self.comment
            )

    async def respond_to_button(self, btn):
        """Respond to the buttons."""
        button_id = btn.data["custom_id"].split()[0]

        if button_id == _ButtonID.WILLPOWER:
            if self.character is not None:
                sup_wp = self.character.superficial_wp + 1
                await self.character.set_superficial_wp(sup_wp)

            await inconnu.character.display(
                btn,
                self.character,
                title="Willpower Spent",
                owner=self.owner,
                fields=[("New WP", inconnu.character.DisplayField.WILLPOWER)],
            )

        elif inconnu.common.contains_digit(button_id):  # Surge buttons are just charids
            self.surged = True
            await inconnu.misc.rouse(btn, 1, self.character, "Surge", False)

        else:
            # We're rerolling
            strategy = button_id
            self.outcome.reroll(strategy)
            self.rerolled = True

            await self.display(btn)

    @property
    def character_name(self) -> str:
        """The character's display name. Either the character name or the player name."""
        if self.character is not None:
            character_name = self.character.name
        else:
            character_name = self.owner.display_name

        return character_name

    @property
    def hunger(self) -> str:
        """
        The Hunger for the roll. This uses the character's Hunger if possible and
        falls back to the hunger dice count if unavailable.
        """
        return self.outcome.hunger.count

    @property
    def comment(self):
        """The original comment, plus any impairment string."""
        if self.character is not None:
            if (impairment := self.character.impairment) is not None:
                comment = (self._comment + "\n") if self._comment else ""
                return comment + impairment
        return self._comment

    @property
    def icon(self) -> str:
        """The icon for the embed."""
        if self.character is not None:
            guild_icon = self.ctx.guild.icon or ""
            icon = inconnu.get_avatar(self.owner) if self.character.is_pc else guild_icon
        else:
            icon = inconnu.get_avatar(self.owner)

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

    async def get_embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.outcome.main_takeaway.upper() + "!"
        if self.rerolled:
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
        if self.outcome.pool <= 30 and await self.use_emoji():
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
            if self.hunger > 0:
                dice = sorted(self.outcome.hunger.dice, reverse=True)
                lines.append("**Hunger Dice:** " + ", ".join(map(str, dice)))

            embed.add_field(
                name=f"Margin: {self.outcome.margin}", value="\n".join(lines), inline=False
            )

        embed.add_field(name="Pool", value=str(self.outcome.pool))
        embed.add_field(name="Hunger", value=str(self.hunger))
        embed.add_field(name="Difficulty", value=str(self.outcome.difficulty))

        if self.outcome.pool_str is not None:
            embed.add_field(name="Pool", value=self.outcome.pool_str)

        # Show what the roll originally was
        if self.rerolled:
            embed.add_field(
                name="Original Outcome",
                value=f"```{self.original_outcome}```",
                inline=False,
            )

        if self.comment is not None:
            embed.set_footer(text=self.comment)

        return embed

    async def use_emoji(self) -> bool:
        """Whether to use emoji in the roll."""
        everyone = self.ctx.guild.default_role
        if not self.ctx.channel.permissions_for(everyone).external_emojis:
            return False

        return not await inconnu.settings.accessible(self.ctx.user)

    @property
    def surging(self) -> bool:
        """Whether the roll uses a Blood Surge."""
        if self.character is None or self.character.splat == "mortal":
            return False

        search = f"{self.outcome.pool_str} {self.comment}"
        match = re.match(r"^.*(\s+surge|surge\s+.*|surge)$", search, re.IGNORECASE | re.DOTALL)
        return match is not None

    @property
    def buttons(self) -> list:
        """Generate the buttons for Willpower re-rolls and surging."""
        buttons = []

        if self.rerolled:
            if self.character is not None:
                buttons.append(
                    Button(
                        label="Mark WP Use",
                        custom_id=_ButtonID.WILLPOWER.unique(),
                        style=discord.ButtonStyle.primary,
                    )
                )
                if not self.surged and self.surging:
                    buttons.append(
                        Button(
                            label="Rouse",
                            custom_id=self.character.id,
                            style=discord.ButtonStyle.danger,
                        )
                    )
            return buttons or None

        # We haven't re-rolled

        if self.outcome.can_reroll:
            buttons.append(
                Button(
                    label="Re-Roll Failures",
                    custom_id=_ButtonID.REROLL_FAILURES.unique(),
                    style=discord.ButtonStyle.primary,
                    disabled=not self.outcome.can_reroll_failures,
                )
            )

            buttons.append(
                Button(
                    label="Max Crits",
                    custom_id=_ButtonID.MAXIMIZE_CRITICALS.unique(),
                    style=discord.ButtonStyle.primary,
                    disabled=not self.outcome.can_maximize_criticals,
                )
            )

            buttons.append(
                Button(
                    label="Avoid Messy",
                    custom_id=_ButtonID.AVOID_MESSY.unique(),
                    style=discord.ButtonStyle.primary,
                    disabled=not self.outcome.can_avoid_messy_critical,
                )
            )

            buttons.append(
                Button(
                    label="Risky Avoid",
                    custom_id=_ButtonID.RISKY_AVOID_MESSY.unique(),
                    style=discord.ButtonStyle.primary,
                    disabled=not self.outcome.can_risky_messy_critical,
                )
            )

        if self.surging:
            buttons.append(
                Button(
                    label="Rouse",
                    custom_id=self.character.id,
                    style=discord.ButtonStyle.danger,
                    row=1,
                )
            )

        return buttons or None
