"""settings.py - User- and server-wide settings."""

from enum import IntEnum, StrEnum, auto
from typing import Any, Callable, Self, cast

import discord
from discord import (
    ButtonStyle,
    ChannelType,
    ComponentType,
    SelectDefaultValue,
    SelectDefaultValueType,
    SelectOption,
)
from discord.ui import Button, Select, TextDisplay
from loguru import logger

from ctx import AppCtx
from inconnu.settings import ExpPerms, VGuild
from inconnu.settings.vuser import VUser
from inconnu.utils import is_admin


class SettingsIDs(IntEnum):
    """Menu item IDs used for quick lookups.

    The order here doesn't matter, as the menu doesn't need stable IDs across
    invocations/processes."""

    EMOJIS = auto()
    OBLIVION = auto()
    RESONANCE = auto()
    EXPERIENCE = auto()
    UPDATES = auto()
    CHANGELOG = auto()
    DELETION = auto()
    MAX_HUNGER = auto()


class OblivionOptions(StrEnum):
    RAW = "1 10"
    ONES = "1"
    TENS = "10"
    NONE = "0"

    @property
    def description(self) -> str:
        """Text representation of the option."""
        match self:
            case OblivionOptions.RAW:
                return "1s and 10s (RAW)"
            case OblivionOptions.ONES:
                return "1s only"
            case OblivionOptions.TENS:
                return "10s only"
            case OblivionOptions.NONE:
                return "Never"

    def to_list(self) -> list[int]:
        """The list value of the setting."""
        if self == OblivionOptions.NONE:
            return []
        return list(map(int, self.split()))

    @classmethod
    def from_list(cls, val: list[int]) -> Self:
        """Construct an OblivionOption from a list."""
        str_val = " ".join(map(str, val))
        return cls(str_val)


class SettingsMenu(discord.ui.DesignerView):
    """The settings menu."""

    def __init__(self, ctx: AppCtx, scope: VGuild | VUser, admin: bool):
        super().__init__(timeout=300, disable_on_timeout=True)
        self.scope = scope

        if isinstance(self.scope, VUser):
            title = "User Settings"
            description = "Update your personal settings. These follow you across servers."
        else:
            title = "Server Settings"
            description = f"Update settings for **{self.scope.name}**."

        container = discord.ui.Container(TextDisplay(f"# {title}\n{description}"))
        self.container = container
        self.add_item(container)
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))

        # Accessibility settings
        container.add_text("## Accessibility")
        button = Button(
            label="Yes" if self.scope.settings.use_emojis else "No",
            style=self.button_style(self.scope.settings.use_emojis),
            id=SettingsIDs.EMOJIS,
            disabled=isinstance(self.scope, VGuild) and not admin,
        )
        button.callback = self.toggle_emojis
        container.add_section(
            TextDisplay("### Use emojis?\nUse custom emojis for dice, damage, etc."),
            accessory=button,
        )

        if isinstance(self.scope, VGuild):
            # GAMEPLAY SETTINGS
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))
            container.add_text("## Gameplay")

            # Empty resonance toggle
            button = Button(
                label="Yes" if self.scope.settings.add_empty_resonance else "No",
                style=self.button_style(self.scope.settings.add_empty_resonance),
                id=SettingsIDs.RESONANCE,
                disabled=not admin,
            )
            button.callback = self.toggle_add_empty_resonance
            resonance_cmd = ctx.bot.cmd_mention("resonance")
            container.add_section(
                TextDisplay(
                    f"### Add empty resonance?\n16.7% chance to appear in {resonance_cmd}."
                ),
                accessory=button,
            )

            container.add_item(discord.ui.Separator())

            # Oblivion stains settings
            current_oblivion = OblivionOptions.from_list(self.scope.settings.oblivion_stains)
            options = [
                SelectOption(label=opt.description, value=opt, default=opt == current_oblivion)
                for opt in list(OblivionOptions)
            ]
            select = Select(
                select_type=ComponentType.string_select,
                options=options,
                id=SettingsIDs.OBLIVION,
                disabled=not admin,
            )
            select.callback = self.set_oblivion_stains
            container.add_text(
                "### Oblivion stains\nWhen to apply Stains for Oblivion Rouse checks."
            )
            container.add_row(select)

            container.add_item(discord.ui.Separator())

            # Max hunger select
            current_max_hunger = str(self.scope.settings.max_hunger)
            options = [
                SelectOption(label="5 (RAW)", value="5", default=current_max_hunger == "5"),
                SelectOption(label="10", value="10", default=current_max_hunger == "10"),
            ]
            select = Select(options=options, id=SettingsIDs.MAX_HUNGER, disabled=not admin)
            select.callback = self.set_max_hunger
            container.add_text("### Max hunger\nOverride standard maximum Hunger rating.")
            container.add_row(select)

            # Experience permissions
            options = [
                SelectOption(
                    label=perm.description,
                    value=perm,
                    default=self.scope.settings.experience_permissions == perm,
                )
                for perm in ExpPerms
            ]
            select = Select(options=options, id=SettingsIDs.EXPERIENCE, disabled=not admin)
            select.callback = self.set_experience_permissions
            container.add_text("### Experience\nSet user permissions for adjusting XP.")
            container.add_row(select)

            # MONITORING SETTINGS
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))
            container.add_text("## Monitoring")

            # Character updates channel
            self._add_channel_select(
                container,
                "### Character updates channel\nDisplay character updates across the server.",
                SettingsIDs.UPDATES,
                self.scope.settings.update_channel,
                self.set_update_channel,
                admin,
            )

            container.add_item(discord.ui.Separator())

            # Rolepost changelog channel
            self._add_channel_select(
                container,
                "### Rolepost changelog channel\nWhere to notify about Rolepost edits.",
                SettingsIDs.CHANGELOG,
                self.scope.settings.changelog_channel,
                self.set_changelog_channel,
                admin,
            )

            container.add_item(discord.ui.Separator())

            # Rolepost deletion channel
            self._add_channel_select(
                container,
                "### Rolepost deletion channel\nWhere to notify about Rolepost deletions.",
                SettingsIDs.DELETION,
                self.scope.settings.deletion_channel,
                self.set_deletion_channel,
                admin,
            )

    @staticmethod
    def button_label(setting: bool) -> str:
        """The button label (Yes/No) for the setting."""
        return "Yes" if setting else "No"

    @staticmethod
    def button_style(setting: bool) -> ButtonStyle:
        """The button style based on the value for the current setting."""
        return ButtonStyle.primary if setting else ButtonStyle.secondary

    def _log_update(self, interaction: discord.Interaction, text: str, val: Any):
        """Log an update event."""
        if interaction.guild is None or interaction.user is None:
            logger.warning("Unable to log: {} -> {}", text, val)
        elif isinstance(self.scope, VGuild):
            logger.info(
                "{} ({}): {} -> {}", interaction.guild.name, interaction.user.name, text, val
            )
        else:
            logger.info("{}: {} -> {}", interaction.user.name, text, val)

    async def toggle_emojis(self, interaction: discord.Interaction):
        """Toggle emoji display (server/user)."""
        self.scope.settings.accessibility = not self.scope.settings.accessibility

        button = cast(Button, self.get_item(SettingsIDs.EMOJIS))
        button.style = self.button_style(self.scope.settings.use_emojis)
        button.label = "Yes" if self.scope.settings.use_emojis else "No"

        await interaction.edit(view=self)
        await self.scope.save()

        self._log_update(interaction, "Use emojis", not self.scope.settings.accessibility)

    async def set_oblivion_stains(self, interaction: discord.Interaction):
        """Set Oblivion stains mode."""
        select = cast(Select, self.get_item(SettingsIDs.OBLIVION))
        self._update_select_default(select, select.values[0])

        stains = OblivionOptions(select.values[0]).to_list()
        vguild = cast(VGuild, self.scope)
        vguild.settings.oblivion_stains = stains

        await interaction.edit(view=self)
        await vguild.save()

        self._log_update(interaction, "Oblivion stains", stains)

    async def toggle_add_empty_resonance(self, interaction: discord.Interaction):
        """Toggle the add empty resonance setting."""
        vguild = cast(VGuild, self.scope)
        vguild.settings.add_empty_resonance = not vguild.settings.add_empty_resonance

        button = cast(Button, self.get_item(SettingsIDs.RESONANCE))
        button.label = self.button_label(vguild.settings.add_empty_resonance)
        button.style = self.button_style(vguild.settings.add_empty_resonance)

        await interaction.edit(view=self)
        await vguild.save()

        self._log_update(interaction, "Add empty resonance", vguild.settings.add_empty_resonance)

    async def set_update_channel(self, interaction: discord.Interaction):
        """Set the update channel by calling the shared setter."""
        await self._set_channel(interaction, SettingsIDs.UPDATES, "update_channel")

    async def set_changelog_channel(self, interaction: discord.Interaction):
        """Set the rolepost changelog channel by calling the shared setter."""
        await self._set_channel(interaction, SettingsIDs.CHANGELOG, "changelog_channel")

    async def set_deletion_channel(self, interaction: discord.Interaction):
        """Set the rolepost deletion channel by calling the shared setter."""
        await self._set_channel(interaction, SettingsIDs.DELETION, "deletion_channel")

    async def set_max_hunger(self, interaction: discord.Interaction):
        """Set the server's max Hunger rating."""
        select = cast(Select, self.get_item(SettingsIDs.MAX_HUNGER))
        new_max_hunger = int(select.values[0])

        self._update_select_default(select, select.values[0])

        vguild = cast(VGuild, self.scope)
        vguild.settings.max_hunger = new_max_hunger

        await interaction.edit(view=self)
        await vguild.save()

        self._log_update(interaction, "Max hunger", new_max_hunger)

    async def set_experience_permissions(self, interaction: discord.Interaction):
        """Set experience permissions."""
        select = cast(Select, self.get_item(SettingsIDs.EXPERIENCE))
        perms = select.values[0]
        self._update_select_default(select, perms)

        vguild = cast(VGuild, self.scope)
        vguild.settings.experience_permissions = ExpPerms(perms)

        await interaction.edit(view=self)
        await vguild.save()

        self._log_update(interaction, "Experience permissions", perms)

    async def _set_channel(
        self,
        interaction: discord.Interaction,
        component: SettingsIDs,
        channel_key: str,
    ):
        """Set the channel and update the select to the new default."""
        if not isinstance(self.scope, VGuild):
            raise ValueError("Expected a VGuild")

        select = cast(Select, self.get_item(component))
        channel = cast(discord.TextChannel, select.values[0])

        setattr(self.scope.settings, channel_key, channel.id)
        select.default_values = [
            SelectDefaultValue(id=channel.id, type=SelectDefaultValueType.channel)
        ]

        await interaction.edit(view=self)
        await self.scope.save()

        self._log_update(interaction, channel_key, f"#{channel.name}")

    @staticmethod
    def _update_select_default(select: Select, val: str):
        """Update a Select's default."""
        for option in select.options:
            option.default = option.value == val

    @staticmethod
    def _add_channel_select(
        container: discord.ui.Container,
        text: str,
        id: SettingsIDs,
        default: int | None,
        callback: Callable,
        admin: bool,
    ):
        """Add a channel select to the container."""
        select = Select(
            select_type=ComponentType.channel_select,
            channel_types=[ChannelType.text],
            id=id,
            disabled=not admin,
        )
        if default is not None:
            select.add_default_value(id=default, type=SelectDefaultValueType.channel)
        select.callback = callback

        container.add_text(text)
        container.add_row(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check that the user is authorized for settings changes."""
        if isinstance(self.scope, VGuild):
            return is_admin(interaction)

        # Users can always change their settings
        return True


async def menu(ctx: AppCtx, scope: str):
    """Present the settings menu."""
    if scope == "guild":
        obj = await VGuild.get_or_fetch(ctx.guild)
    else:
        obj = await VUser.get_or_fetch(ctx.user.id)

    view = SettingsMenu(ctx, obj, is_admin(ctx))
    await ctx.respond(view=view)


# Accessibility


async def accessible(ctx: AppCtx | discord.Interaction):
    """Determine whether we should use accessibility mode.

    Accessibility mode disables emojis. Recommended to instead use can_emoji()
    instead, as it's easier to reason about."""
    # User accessibility trumps guild accessibility
    user_settings = await VUser.get_or_fetch(ctx.user.id)
    if user_settings.settings.accessibility:
        return True

    # Check guild accessibility
    guild = await VGuild.get_or_fetch(ctx.guild)
    if guild.settings.accessibility:
        return True

    # Finally, make sure we have emoji permission
    try:
        everyone = ctx.guild.default_role
        return not ctx.channel.permissions_for(everyone).external_emojis
    except AttributeError:
        # We somehow received a PartialMessageable or something else
        return True  # Fallback


async def can_emoji(ctx: AppCtx | discord.Interaction) -> bool:
    """Wrapper for accessible() that simply inverts the logic."""
    return not await accessible(ctx)


# XP Permissions


async def can_adjust_current_xp(ctx: AppCtx) -> bool:
    """Whether the user can adjust their current XP."""
    if is_admin(ctx):
        return True

    guild = await VGuild.get_or_fetch(ctx.guild)
    return guild.settings.experience_permissions in [
        ExpPerms.UNRESTRICTED,
        ExpPerms.UNSPENT_ONLY,
    ]


async def can_adjust_lifetime_xp(ctx: AppCtx) -> bool:
    """Whether the user has permission to adjust lifetime XP."""
    if is_admin(ctx):
        return True

    guild = await VGuild.get_or_fetch(ctx.guild)
    return guild.settings.experience_permissions in [
        ExpPerms.UNRESTRICTED,
        ExpPerms.LIFETIME_ONLY,
    ]


# Oblivion stains


async def oblivion_stains(guild: discord.Guild) -> list:
    """Retrieve the Rouse results that grant Oblivion stains."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.oblivion_stains


# Update Channels


async def update_channel(guild: discord.Guild):
    """Retrieve the ID of the guild's update channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    if update_channel := vguild.settings.update_channel:
        return guild.get_channel(update_channel)

    return None


async def changelog_channel(guild: discord.Guild) -> int | None:
    """Retrieves the ID of the guild's RP changelog channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.changelog_channel


async def deletion_channel(guild: discord.Guild) -> int | None:
    """Retrieves the ID of the guild's RP deletion channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.deletion_channel


async def add_empty_resonance(guild: discord.Guild):
    """Whether to add Empty Resonance to the Resonance table."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.add_empty_resonance


async def max_hunger(guild: discord.Guild):
    """Get the max Hunger rating allowed in rolls."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.max_hunger
