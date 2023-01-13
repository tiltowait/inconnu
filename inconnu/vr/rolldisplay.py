"""rolldisplay.py - A class for managing the display of roll outcomes and rerolls."""
# pylint: disable=too-many-arguments, too-many-instance-attributes

import re
import uuid
from enum import Enum

import discord
from discord.ui import Button

import inconnu
from config import web_asset
from inconnu.vr import dicemoji


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

    def __init__(self, has_character, callback, timeout_handler, owner, buttons):
        super().__init__(timeout=600)
        self.has_character = has_character
        self.callback = callback
        self.timeout_handler = timeout_handler
        self.owner = owner

        stop = True
        for button in buttons:
            if not button.disabled:
                stop = False
            button.callback = self.button_pressed
            self.add_item(button)

        if stop:
            # All of the buttons are disabled, so we don't need to listen
            self.stop()

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

    async def on_timeout(self):
        """Inform the RollDisplay that we've timed out."""
        await super().on_timeout()
        if self.timeout_handler is not None:
            await self.timeout_handler()


class RollDisplay:
    """Display and manipulate roll outcomes. Provides buttons for rerolls, wp, and rouse."""

    def __init__(self, ctx, outcome, comment, character, owner, listener, timeout):
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
        self.listener = listener
        self.timeout_handler = timeout

    async def display(self, alt_ctx=None):
        """Display the roll."""
        # We might be responding to a button
        ctx = alt_ctx or self.ctx
        msg_contents = {}

        if buttons := self.buttons:
            self.controls = _RollControls(
                self.character is not None,
                self.respond_to_button,
                self.reroll_timeout,
                self.owner,
                buttons,
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
                inter = await ctx.edit_original_response(**msg_contents)

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
                ctx.guild.id,
                ctx.channel.id,
                self.owner.id,
                msg_id,
                self.character,
                self.outcome,
                self.comment,
            )
        else:
            # If this is a DM roll, we don't keep stats, so we don't need to
            # get the message ID
            await inconnu.stats.log_roll(
                None, None, self.owner.id, None, self.character, self.outcome, self.comment
            )

    async def respond_to_button(self, btn):
        """Respond to the buttons."""
        button_id = btn.data["custom_id"].split()[0]

        if button_id == _ButtonID.WILLPOWER:
            if self.character is not None:
                sup_wp = self.character.superficial_wp + 1
                self.character.set_superficial_wp(sup_wp)
                await self.character.commit()

            await inconnu.character.display(
                btn,
                self.character,
                title="Willpower Spent",
                owner=self.owner,
                fields=[("New WP", inconnu.character.DisplayField.WILLPOWER)],
            )

        elif inconnu.common.contains_digit(button_id):  # Surge buttons are just charids
            self.surged = True
            await inconnu.misc.rouse(btn, self.character, 1, "Surge", False)

        else:
            # We're rerolling
            strategy = button_id
            self.outcome.reroll(strategy)
            self.rerolled = True

            await self.display(btn)
            if self.listener:
                await self.listener(btn, self.character, self.outcome)

    async def reroll_timeout(self):
        """Inform the listener we have timed out."""
        if self.timeout_handler is not None:
            await self.timeout_handler(self.outcome)

    @property
    def character_name(self) -> str:
        """The character's display name. Either the character name or the player name."""
        if self.character is not None:
            character_name = self.character.name
        else:
            character_name = self.owner.display_name

        return character_name

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
            else:
                return "*Mortal*"

        # We were given a specific Hunger (or implicit 0), a character wasn't
        # given, or possibly both.
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
        can_emoji = await inconnu.settings.can_emoji(self.ctx)
        if self.outcome.pool <= 30 and can_emoji:
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
            if isinstance(self.hunger, str):
                lines.append("**Hunger:** Mortal")
            elif self.hunger > 0:
                dice = sorted(self.outcome.hunger.dice, reverse=True)
                lines.append("**Hunger Dice:** " + ", ".join(map(str, dice)))
            else:
                lines.append("**Hunger:** None")

            embed.add_field(
                name=f"Margin: {self.outcome.margin}", value="\n".join(lines), inline=False
            )

        embed.add_field(name="Pool", value=str(self.outcome.pool))
        embed.add_field(name="Hunger", value=self.hunger)
        embed.add_field(name="Difficulty", value=str(self.outcome.difficulty))

        if self.outcome.pool_str:
            # If trait names are in CamelCase or snake_case, we want to
            # convert them to something more easily read

            # First, remove snake_case
            pool_str = self.outcome.pool_str.replace("_", " ")

            # Add spaces before "Camel", and add spaces before "XYZ", then
            # split and rejoin to remove the extraneous spaces
            splitted = re.sub("([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", pool_str)).split()

            # Uppercase each word in the pool. We can't use .title(), because
            # .title() will make everything else lowercase. "XYZ" would become
            # "Xyz", which is not desired.
            splitted = map(lambda t: (t[0].upper() + t[1:]) if t[0].islower() else t, splitted)

            pool_str = " ".join(splitted)
            embed.add_field(name="Pool", value=pool_str)

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

        if not self.outcome.can_reroll:
            # They don't have any Attributes in their pool. This will only show
            # if they used a trait in the roll. If they just used numbers, then
            # they will always get re-roll buttons.
            buttons.append(
                Button(
                    label="WP Unavailable (p.158)",
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                )
            )
        else:
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
