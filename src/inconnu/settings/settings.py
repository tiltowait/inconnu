"""settings.py - User- and server-wide settings."""

from enum import IntEnum, auto
from typing import Callable, cast

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

import inconnu
from ctx import AppCtx
from inconnu.settings import ExpPerms, VGuild
from inconnu.settings.vuser import VUser


class SettingsIDs(IntEnum):
    EMOJIS = auto()
    OBLIVION = auto()
    RESONANCE = auto()
    UPDATES = auto()


class SettingsMenu(discord.ui.DesignerView):
    """The settings menu."""

    def __init__(self, ctx: AppCtx, scope: VGuild | VUser):
        super().__init__(timeout=300, disable_on_timeout=True)
        self.scope = scope

        if isinstance(self.scope, VUser):
            title = "User Settings"
            description = "Update your personal settings. These follow you across servers."
        else:
            title = "Server Settings"
            description = f"Update settings for **{self.scope.name}**."

        container = discord.ui.Container(TextDisplay(f"## {title}\n{description}"))
        self.container = container
        self.add_item(container)
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))

        # Accessibility settings
        button = Button(
            label="Yes" if self.scope.settings.use_emojis else "No",
            style=self.button_style(self.scope.settings.use_emojis),
            id=SettingsIDs.EMOJIS,
        )
        button.callback = self.toggle_emojis
        container.add_section(
            TextDisplay("### Use emojis?\nUse custom emojis for dice, damage, etc."),
            accessory=button,
        )

        if isinstance(self.scope, VGuild):
            container.add_item(discord.ui.Separator())

            # Oblivion stains settings
            if not self.scope.settings.oblivion_stains:
                oblivion_raw = "0"
            elif len(self.scope.settings.oblivion_stains) == 2:
                oblivion_raw = "100"
            elif self.scope.settings.oblivion_stains[0] == 10:
                oblivion_raw = "10"
            else:
                oblivion_raw = "1"
            options = [
                SelectOption(label="1s and 10s (RAW)", value="100", default=oblivion_raw == "100"),
                SelectOption(label="1s only", value="1", default=oblivion_raw == "1"),
                SelectOption(label="10s only", value="10", default=oblivion_raw == "10"),
                SelectOption(label="Never", value="0", default=oblivion_raw == "0"),
            ]
            select = Select(
                select_type=ComponentType.string_select,
                options=options,
                id=SettingsIDs.OBLIVION,
            )
            select.callback = self.set_oblivion_stains
            container.add_text(
                "### Oblivion stains\nWhen to apply Stains for Oblivion Rouse checks."
            )
            container.add_row(select)

            container.add_item(discord.ui.Separator())

            # Updates channel
            self._add_channel_select(
                container,
                "### Updates channel\nDisplay character updates across the server.",
                self.scope.settings.update_channel,
                self.set_update_channel,
            )

            container.add_item(discord.ui.Separator())

            # TODO: Changelog channel
            # TODO: Deletion channel

            # Empty resonance toggle
            button = Button(
                label="Yes" if self.scope.settings.add_empty_resonance else "No",
                style=self.button_style(self.scope.settings.add_empty_resonance),
                id=SettingsIDs.RESONANCE,
            )
            button.callback = self.toggle_add_empty_resonance
            resonance_cmd = ctx.bot.cmd_mention("resonance")
            container.add_section(
                TextDisplay(
                    f"### Add empty resonance?\n16.7% chance to appear in {resonance_cmd}."
                ),
                accessory=button,
            )

            # TODO: Max hunger

    @staticmethod
    def button_label(setting: bool) -> str:
        """The button label (Yes/No) for the setting."""
        return "Yes" if setting else "No"

    @staticmethod
    def button_style(setting: bool) -> ButtonStyle:
        """The button style based on the value for the current setting."""
        return ButtonStyle.primary if setting else ButtonStyle.secondary

    async def toggle_emojis(self, interaction: discord.Interaction):
        """Toggle emoji display (server/user)."""
        self.scope.settings.accessibility = not self.scope.settings.accessibility

        button = cast(Button, self.get_item(SettingsIDs.EMOJIS))
        button.style = self.button_style(self.scope.settings.use_emojis)
        button.label = "Yes" if self.scope.settings.use_emojis else "No"

        await interaction.edit(view=self)
        await self.scope.save()

    async def set_oblivion_stains(self, interaction: discord.Interaction):
        """Set Oblivion stains mode."""
        select = cast(Select, self.get_item(SettingsIDs.OBLIVION))

        if select.values[0] == "100":
            stains = [1, 10]
            self._update_select_default(select, 0)
        elif select.values[0] == "1":
            stains = [1]
            self._update_select_default(select, 1)
        elif select.values[0] == "10":
            stains = [10]
            self._update_select_default(select, 2)
        else:
            stains = []
            self._update_select_default(select, 3)

        vguild = cast(VGuild, self.scope)
        vguild.settings.oblivion_stains = stains
        print(vguild.settings.oblivion_stains)

        await interaction.edit(view=self)
        await vguild.save()

    async def toggle_add_empty_resonance(self, interaction: discord.Interaction):
        """Toggle the add empty resonance setting."""
        vguild = cast(VGuild, self.scope)
        vguild.settings.add_empty_resonance = not vguild.settings.add_empty_resonance

        button = cast(Button, self.get_item(SettingsIDs.RESONANCE))
        button.label = self.button_label(vguild.settings.add_empty_resonance)
        button.style = self.button_style(vguild.settings.add_empty_resonance)

        await interaction.edit(view=self)
        await vguild.save()

    async def set_update_channel(self, interaction: discord.Interaction):
        """Set the update channel by calling the shared setter."""
        await self._set_channel(interaction, SettingsIDs.UPDATES, "update_channel")

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
        channel = select.values[0]

        setattr(self.scope.settings, channel_key, channel.id)
        select.default_values = [
            SelectDefaultValue(id=channel.id, type=SelectDefaultValueType.channel)
        ]

        await interaction.edit(view=self)
        await self.scope.save()

    @staticmethod
    def _update_select_default(select: Select, idx: int):
        """Update a Select's default."""
        for i, option in enumerate(select.options):
            option.default = i == idx

    @staticmethod
    def _add_channel_select(
        container: discord.ui.Container,
        text: str,
        default: int | None,
        callback: Callable,
    ):
        """Add a channel select to the container."""
        select = Select(
            select_type=ComponentType.channel_select,
            channel_types=[ChannelType.text],
            id=SettingsIDs.UPDATES,
        )
        if default is not None:
            select.add_default_value(id=default, type=SelectDefaultValueType.channel)
        select.callback = callback

        container.add_text(text)
        container.add_row(select)


async def edit_settings(ctx: AppCtx):
    """Present the settings menu."""
    guild = await VGuild.get_or_fetch(ctx.guild)

    view = SettingsMenu(ctx, guild)
    await ctx.respond(view=view)


class Settings:
    """A class for managing individual and server-wide settings."""

    _user_cache = {}

    # Accessibility

    async def accessible(self, ctx: AppCtx | discord.Interaction):
        """Determine whether we should use accessibility mode."""
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

    async def can_emoji(self, ctx: AppCtx | discord.Interaction) -> bool:
        """Wrapper for accessible() that simply inverts the logic."""
        return not await self.accessible(ctx)

    async def set_accessibility(self, ctx, enabled: bool, scope: str):
        """
        Set the accessibility mode.
        Args:
            ctx: Discord context
            enabled (bool): The accessibility toggle
            scope (str): "user" or "server"
        """
        if scope == "user":
            await self._set_key(ctx.user, "accessibility", enabled)

            if enabled:
                response = "**Accessibility mode** enabled."
            else:
                response = "**Accessibility mode** disabled. Note: the server may override."
        else:  # Server-wide setting
            if not ctx.user.guild_permissions.administrator:
                raise PermissionError("Sorry, only admins can set server-wide accessibility mode.")

            await self._set_key(ctx.guild, "accessibility", enabled)

            if enabled:
                response = "**Accessibility mode** enabled server-wide."
            else:
                response = "**Accessibility mode** disabled server-wide. Users may override."

        return response

    # XP Permissions

    async def can_adjust_current_xp(self, ctx) -> bool:
        """Whether the user can adjust their current XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await VGuild.get_or_fetch(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.UNSPENT_ONLY,
        ]

    async def can_adjust_lifetime_xp(self, ctx) -> bool:
        """Whether the user has permission to adjust lifetime XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await VGuild.get_or_fetch(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.LIFETIME_ONLY,
        ]

    async def xp_permissions(self, guild) -> str:
        """Get the XP permissions."""
        guild = await VGuild.get_or_fetch(guild)

        match guild.settings.experience_permissions:
            case ExpPerms.UNSPENT_ONLY:
                return "Users may adjust unspent XP only."
            case ExpPerms.LIFETIME_ONLY:
                return "Users may adjust lifetime XP only."
            case ExpPerms.ADMIN_ONLY:
                return "Only admins may adjust XP totals."
            case _:
                return "Users may adjust unspent and lifetime XP."

    async def set_xp_permissions(self, ctx, permissions):
        """
        Set the XP settings:
            • User can modify current and lifetime
            • User can modify current
            • User can modify lifetime
            • User can't modify any
        """
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set user experience permissions.")

        await self._set_key(ctx.guild, "experience_permissions", permissions)

        match ExpPerms(permissions):
            case ExpPerms.UNRESTRICTED:
                response = "Users have unrestricted XP access."
            case ExpPerms.UNSPENT_ONLY:
                response = "Users may only adjust unspent XP."
            case ExpPerms.LIFETIME_ONLY:
                response = "Users may only adjust lifetime XP."
            case ExpPerms.ADMIN_ONLY:
                response = "Only admins may adjust user XP."

        return response

    # Oblivion stains

    async def oblivion_stains(self, guild) -> list:
        """Retrieve the Rouse results that grant Oblivion stains."""
        guild = await VGuild.get_or_fetch(guild)
        return guild.settings.oblivion_stains

    async def set_oblivion_stains(self, ctx, stains: int):
        """Set which dice outcomes will give stains for Oblivion rouse checks."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set Oblivion rouse check stains.")

        response = "**Rouse checks:** Warn for Oblivion stains when rolling "

        if stains == 100:
            stains = [1, 10]
            response += "`1` or `10`."
        elif stains == 0:
            stains = []
            response = "**Rouse checks:** Oblivion Rouses never give stains."
        else:
            response += f"`{stains}`."
            stains = [stains]

        await self._set_key(ctx.guild, "oblivion_stains", stains)
        return response

    # Update Channels

    async def _set_channel(
        self,
        ctx: AppCtx,
        channel: discord.TextChannel | None,
        key: str,
    ):
        """Set the guild channel for a given key."""
        option_name = key.replace("_", " ")

        if not ctx.user.guild_permissions.administrator:
            raise PermissionError(f"Sorry, only admins can set the {option_name} channel.")

        if channel:
            await self._set_key(ctx.guild, key, channel.id)
            return f"Set the {option_name} to {channel.mention}."

        # Un-setting
        await self._set_key(ctx.guild, key, None)
        return f"Un-set the {option_name}."

    async def update_channel(self, guild: discord.Guild):
        """Retrieve the ID of the guild's update channel, if any."""
        vguild = await VGuild.get_or_fetch(guild)
        if update_channel := vguild.settings.update_channel:
            return guild.get_channel(update_channel)

        return None

    async def set_update_channel(self, ctx, channel: discord.TextChannel | None):
        """Set the guild's update channel."""
        return await self._set_channel(ctx, channel, "update_channel")

    async def changelog_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP changelog channel, if any."""
        vguild = await VGuild.get_or_fetch(guild)
        return vguild.settings.changelog_channel

    async def set_changelog_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP changelog channel."""
        return await self._set_channel(ctx, channel, "changelog_channel")

    async def deletion_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP deletion channel, if any."""
        vguild = await VGuild.get_or_fetch(guild)
        return vguild.settings.deletion_channel

    async def set_deletion_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP deletion channel."""
        return await self._set_channel(ctx, channel, "deletion_channel")

    async def add_empty_resonance(self, guild: discord.Guild):
        """Whether to add Empty Resonance to the Resonance table."""
        vguild = await VGuild.get_or_fetch(guild)
        return vguild.settings.add_empty_resonance

    async def set_empty_resonance(self, ctx, add_empty: bool) -> str:
        """Set whether to add Empty Resonance to the Resonance table."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set Oblivion rouse check stains.")

        await self._set_key(ctx.guild, "add_empty_resonance", add_empty)
        will_or_not = "will" if add_empty else "will not"

        return f"Empty Resonance **{will_or_not}** be added to the Resonance table."

    async def max_hunger(self, guild: discord.Guild):
        """Get the max Hunger rating allowed in rolls."""
        vguild = await VGuild.get_or_fetch(guild)
        return vguild.settings.max_hunger

    async def set_max_hunger(self, ctx, max_hunger: int) -> str:
        """Set the max Hunger rating to 5 or 10."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set the max Hunger rating.")

        await self._set_key(ctx.guild, "max_hunger", max_hunger)
        return f"Max Hunger rating is now `{max_hunger}`."

    async def _set_key(self, scope, key: str, value):
        """
        Enable or disable a setting.
        Args:
            scope (discord.Guild | discord.Member): user or guild
            key (str): The setting key
            value: The value to set
        """
        if isinstance(scope, discord.Guild):
            await self._set_guild(scope, key, value)
        elif isinstance(scope, discord.Member):
            await self._set_user(scope, key, value)
        else:
            return ValueError(f"Unknown scope `{scope}`.")

        return True

    async def _set_guild(self, guild: discord.Guild, key: str, value):
        """Enable or disable a guild setting."""
        res = await inconnu.db.guilds.update_one(
            {"guild": guild.id}, {"$set": {f"settings.{key}": value}}
        )
        if res.matched_count == 0:
            await inconnu.db.guilds.insert_one({"guild": guild.id, "settings": {key: value}})

        # Update the cache
        logger.info("SETTINGS: {} (guild): {}={}", guild.name, key, value)
        guild = await VGuild.get_or_fetch(guild)
        setattr(guild, key, value)

    async def _set_user(self, user: discord.Member, key: str, value):
        """Enable or disable a user setting."""
        res = await inconnu.db.users.update_one(
            {"user": user.id}, {"$set": {f"settings.{key}": value}}
        )
        if res.matched_count == 0:
            await inconnu.db.users.insert_one({"user": user.id, "settings": {key: value}})

        # Update the cache
        logger.info("SETTINGS: {}: {}={}", user.name, key, value)

        user_settings = await self._fetch_user(user)
        setattr(user_settings.settings, key, value)
        await user_settings.save()

    async def _fetch_user(self, user: discord.User) -> VUser:
        """Fetch a user."""
        if not isinstance(user, int):
            user = user.id

        if user_settings := self._user_cache.get(user):
            # User is in the cache
            return user_settings

        # User not in the cache
        if (user_settings := await VUser.find_one({"user": user})) is None:
            # User is not in the database, so we create a new one
            user_settings = VUser(user=user)

        # Add the user settings to the cache and return
        self._user_cache[user] = user_settings
        return user_settings
