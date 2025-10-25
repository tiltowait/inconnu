"""settings.py - User- and server-wide settings."""

import discord
from loguru import logger

import inconnu
from inconnu.settings import ExpPerms, GuildSettings
from inconnu.settings.vuser import VUser


class Settings:
    """A class for managing individual and server-wide settings."""

    _guild_cache = {}
    _user_cache = {}

    # Accessibility

    async def accessible(self, ctx: discord.ApplicationContext | discord.Interaction):
        """Determine whether we should use accessibility mode."""
        # User accessibility trumps guild accessibility
        user_settings = await self._fetch_user(ctx.user)
        if user_settings.settings.accessibility:
            return True

        if ctx.guild is None:
            # This is in a DM, so there is no server to check
            return False

        # Check guild accessibility
        guild = await self._fetch_guild(ctx.guild)
        if guild.accessibility:
            return True

        # Finally, make sure we have emoji permission
        try:
            everyone = ctx.guild.default_role
            return not ctx.channel.permissions_for(everyone).external_emojis
        except AttributeError:
            # We somehow received a PartialMessageable or something else
            return True  # Fallback

    async def can_emoji(self, ctx: discord.ApplicationContext | discord.Interaction) -> bool:
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

        guild = await self._fetch_guild(ctx.guild)
        return guild.experience_permissions in [ExpPerms.UNRESTRICTED, ExpPerms.UNSPENT_ONLY]

    async def can_adjust_lifetime_xp(self, ctx) -> bool:
        """Whether the user has permission to adjust lifetime XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await self._fetch_guild(ctx.guild)
        return guild.experience_permissions in [ExpPerms.UNRESTRICTED, ExpPerms.LIFETIME_ONLY]

    async def xp_permissions(self, guild):
        """Get the XP permissions."""
        guild = await self._fetch_guild(guild)

        match guild.experience_permissions:
            case ExpPerms.UNRESTRICTED:
                return "Users may adjust unspent and lifetime XP."
            case ExpPerms.UNSPENT_ONLY:
                return "Users may adjust unspent XP only."
            case ExpPerms.LIFETIME_ONLY:
                return "Users may adjust lifetime XP only."
            case ExpPerms.ADMIN_ONLY:
                return "Only admins may adjust XP totals."

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
        guild = await self._fetch_guild(guild)
        return guild.oblivion_stains

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
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
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
        guild_settings = await self._fetch_guild(guild)
        if update_channel := guild_settings.update_channel:
            return guild.get_channel(update_channel)

        return None

    async def set_update_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's update channel."""
        return await self._set_channel(ctx, channel, "update_channel")

    async def changelog_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP changelog channel, if any."""
        guild_settings = await self._fetch_guild(guild)
        return guild_settings.changelog_channel

    async def set_changelog_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP changelog channel."""
        return await self._set_channel(ctx, channel, "changelog_channel")

    async def deletion_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP deletion channel, if any."""
        guild_settings = await self._fetch_guild(guild)
        return guild_settings.deletion_channel

    async def set_deletion_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP deletion channel."""
        return await self._set_channel(ctx, channel, "deletion_channel")

    async def add_empty_resonance(self, guild: discord.Guild):
        """Whether to add Empty Resonance to the Resonance table."""
        guild = await self._fetch_guild(guild)
        return guild.add_empty_resonance

    async def set_empty_resonance(self, ctx, add_empty: bool) -> str:
        """Set whether to add Empty Resonance to the Resonance table."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set Oblivion rouse check stains.")

        await self._set_key(ctx.guild, "add_empty_resonance", add_empty)
        will_or_not = "will" if add_empty else "will not"

        return f"Empty Resonance **{will_or_not}** be added to the Resonance table."

    async def max_hunger(self, guild: discord.Guild):
        """Get the max Hunger rating allowed in rolls."""
        guild = await self._fetch_guild(guild)
        return guild.max_hunger

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
        guild = await self._fetch_guild(guild)
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
        await user_settings.commit()

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

    async def _fetch_guild(self, guild: discord.Guild | int | None) -> GuildSettings:
        """Fetch a guild."""
        if guild is None:
            # We're in DMs
            return GuildSettings({})

        if isinstance(guild, discord.Guild):
            guild_id = guild.id
        else:
            guild_id = guild

        if guild_settings := self._guild_cache.get(guild_id):
            return guild_settings

        guild_params = await inconnu.db.guilds.find_one({"guild": guild_id}) or {}
        if not guild_params:
            # In case we missed them somehow
            await inconnu.stats.guild_joined(guild)

        guild_settings = GuildSettings(guild_params)
        self._guild_cache[guild_id] = guild_settings

        return guild_settings
