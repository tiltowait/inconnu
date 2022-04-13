"""settings.py - User- and server-wide settings."""

import discord

import inconnu

from .guildsettings import ExpPerms, Guild


class Settings:
    """A class for managing individual and server-wide settings."""

    _guild_cache = {}
    _user_cache = {}

    # Accessibility

    async def accessible(self, user: discord.User | discord.Member):
        """Determine whether we should use accessibility mode."""
        user_settings = await self._fetch_user(user)
        if user_settings.get("settings", {}).get("accessibility", False):
            return True

        guild = await self._fetch_guild(user.guild)
        return guild.settings.accessibility

    async def set_accessibility(self, ctx: discord.ApplicationContext, enabled: bool, scope: str):
        """
        Set the accessibility mode.
        Args:
            ctx: Discord context
            enabled (bool): The accessibility toggle
            scope (str): "user" or "server"
        """
        if scope == "user":
            await self._set_user(ctx.user, "accessibility", enabled)

            if enabled:
                response = "**Accessibility mode** enabled."
            else:
                response = "**Accessibility mode** disabled. Note: the server may override."
        else:  # Server-wide setting
            if not ctx.user.guild_permissions.administrator:
                raise PermissionError("Sorry, only admins can set server-wide accessibility mode.")

            guild = await self._fetch_guild(ctx.guild)
            guild.settings.accessibility = enabled
            await guild.commit()

            if enabled:
                response = "**Accessibility mode** enabled server-wide."
            else:
                response = "**Accessibility mode** disabled server-wide. Users may override."

        return response

    # XP Permissions

    async def can_adjust_current_xp(self, ctx: discord.ApplicationContext) -> bool:
        """Whether the user can adjust their current XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await self._fetch_guild(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.UNSPENT_ONLY,
        ]

    async def can_adjust_lifetime_xp(self, ctx: discord.ApplicationContext) -> bool:
        """Whether the user has permission to adjust lifetime XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await self._fetch_guild(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.LIFETIME_ONLY,
        ]

    async def xp_permissions(self, guild: discord.Guild):
        """Get the XP permissions."""
        guild = await self._fetch_guild(guild)

        match guild.settings.experience_permissions:
            case ExpPerms.UNRESTRICTED:
                return "Users may adjust unspent and lifetime XP."
            case ExpPerms.UNSPENT_ONLY:
                return "Users may adjust unspent XP only."
            case ExpPerms.LIFETIME_ONLY:
                return "Users may adjust lifetime XP only."
            case ExpPerms.ADMIN_ONLY:
                return "Only admins may adjust XP totals."

    async def set_xp_permissions(self, ctx: discord.ApplicationContext, permissions: str):
        """
        Set the XP settings:
            • User can modify current and lifetime
            • User can modify current
            • User can modify lifetime
            • User can't modify any
        """
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set user experience permissions.")

        guild = await self._fetch_guild(ctx.guild)
        guild.settings.experience_permissions = permissions
        await guild.commit()

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

    async def oblivion_stains(self, guild: discord.Guild) -> list:
        """Retrieve the Rouse results that grant Oblivion stains."""
        guild = await self._fetch_guild(guild)
        return guild.settings.oblivion_stains

    async def set_oblivion_stains(self, ctx: discord.ApplicationContext, stains: int):
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

        guild = await self._fetch_guild(ctx.guild)
        guild.settings.oblivion_stains = stains
        await guild.commit()
        return response

    # Update Channels

    async def update_channel(self, guild: discord.Guild):
        """Retrieve the ID of the guild's update channel, if any."""
        guild_settings = await self._fetch_guild(guild)

        if update_channel := guild_settings.settings.update_channel:
            return guild.get_channel(update_channel)

        return None

    async def set_update_channel(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel
    ):
        """Set the guild's update channel."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set Oblivion rouse check stains.")

        guild = await self._fetch_guild(ctx.guild)

        if channel:
            guild.settings.update_channel = channel.id
            await guild.commit()
            return f"Set update channel to {channel.mention}."

        # Un-setting
        guild.settings.update_channel = None
        await guild.commit()
        return "Un-set the update channel."

    async def _set_user(self, user: discord.Member, key: str, value):
        """Enable or disable a user setting."""
        res = await inconnu.database.users.update_one(
            {"user": user.id}, {"$set": {f"settings.{key}": value}}
        )
        if res.matched_count == 0:
            await inconnu.database.users.insert_one({"user": user.id, "settings": {key: value}})

        # Update the cache
        user_settings = await self._fetch_user(user)
        user_settings.setdefault("settings", {})[key] = value
        self._user_cache[user.id] = user_settings

    async def _fetch_user(self, user: discord.User):
        """Fetch a user."""
        if not isinstance(user, int):
            user = user.id

        if user_settings := self._user_cache.get(user):
            return user_settings

        # See if it's in the database
        if not (user_settings := await inconnu.database.users.find_one({"user": user})):
            user_settings = {"user": user}

        self._user_cache[user] = user_settings

        return user_settings

    async def _fetch_guild(self, guild: discord.Guild) -> Guild:
        """Fetch a guild."""
        if guild_settings := self._guild_cache.get(guild.id):
            return guild_settings

        if not (guild_settings := await Guild.find_one({"guild": guild.id})):
            # Make the guild
            # await inconnu.stats.guild_joined(guild)
            print("Gotta make the guild, son")

        self._guild_cache[guild.id] = guild_settings

        return guild_settings
