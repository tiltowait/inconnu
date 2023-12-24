"""settings.py - User- and server-wide settings."""

import discord

from inconnu.settings import ExpPerms, VGuild
from inconnu.settings.vuser import VUser


class Settings:
    """A class for managing individual and server-wide settings."""

    _guild_cache = {}
    _user_cache = {}

    # Accessibility

    async def accessible(self, ctx: discord.ApplicationContext | discord.Interaction):
        """Determine whether we should use accessibility mode."""
        # User accessibility trumps guild accessibility
        user_settings = await self.find_user(ctx.user)
        if user_settings.settings.accessibility:
            return True

        if ctx.guild is None:
            # This is in a DM, so there is no server to check
            return False

        # Check guild accessibility
        guild = await self.find_guild(ctx.guild)
        if guild.settings.accessibility:
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
            user = await self.find_user(ctx.user)
            user.settings.accessibility = enabled
            await user.save_changes()

            if enabled:
                response = "**Accessibility mode** enabled."
            else:
                response = "**Accessibility mode** disabled. Note: the server may override."
        else:  # Server-wide setting
            if not ctx.user.guild_permissions.administrator:
                raise PermissionError("Sorry, only admins can set server-wide accessibility mode.")

            vguild = await self.find_guild(ctx.guild)
            vguild.settings.accessibility = enabled
            await vguild.save_changes()

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

        guild = await self.find_guild(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.UNSPENT_ONLY,
        ]

    async def can_adjust_lifetime_xp(self, ctx) -> bool:
        """Whether the user has permission to adjust lifetime XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        guild = await self.find_guild(ctx.guild)
        return guild.settings.experience_permissions in [
            ExpPerms.UNRESTRICTED,
            ExpPerms.LIFETIME_ONLY,
        ]

    async def xp_permissions(self, guild):
        """Get the XP permissions."""
        guild = await self.find_guild(guild)

        match guild.settings.experience_permissions:
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

        vguild = await self.find_guild(ctx.guild)
        vguild.settings.experience_permissions = permissions
        await vguild.save_changes()

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
        guild = await self.find_guild(guild)
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

        vguild = await self.find_guild(ctx.guild)
        vguild.settings.oblivion_stains = stains
        await vguild.save_changes()

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

        vguild = await self.find_guild(ctx.guild)

        if channel:
            setattr(vguild.settings, key, channel.id)
            await vguild.save_changes()

            return f"Set the {option_name} to {channel.mention}."

        # Un-setting
        setattr(vguild.settings, key, None)
        await vguild.save_changes()

        return f"Un-set the {option_name}."

    async def update_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Retrieve the ID of the guild's update channel, if any."""
        vguild = await self.find_guild(guild)
        if update_channel := vguild.settings.update_channel:
            return guild.get_channel(update_channel)

        return None

    async def set_update_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's update channel."""
        return await self._set_channel(ctx, channel, "update_channel")

    async def changelog_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP changelog channel, if any."""
        guild = await self.find_guild(guild)
        return guild.settings.changelog_channel

    async def set_changelog_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP changelog channel."""
        return await self._set_channel(ctx, channel, "changelog_channel")

    async def deletion_channel(self, guild: discord.Guild) -> int | None:
        """Retrieves the ID of the guild's RP deletion channel, if any."""
        guild = await self.find_guild(guild)
        return guild.settings.deletion_channel

    async def set_deletion_channel(self, ctx, channel: discord.TextChannel):
        """Set the guild's RP deletion channel."""
        return await self._set_channel(ctx, channel, "deletion_channel")

    async def add_empty_resonance(self, guild: discord.Guild):
        """Whether to add Empty Resonance to the Resonance table."""
        guild = await self.find_guild(guild)
        return guild.settings.add_empty_resonance

    async def set_empty_resonance(self, ctx, add_empty: bool) -> str:
        """Set whether to add Empty Resonance to the Resonance table."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set Oblivion rouse check stains.")

        vguild = await self.find_guild(ctx.guild)
        vguild.settings.add_empty_resonance = add_empty
        await vguild.save_changes()

        will_or_not = "will" if add_empty else "will not"
        return f"Empty Resonance **{will_or_not}** be added to the Resonance table."

    async def max_hunger(self, guild: discord.Guild):
        """Get the max Hunger rating allowed in rolls."""
        guild = await self.find_guild(guild)
        return guild.settings.max_hunger

    async def set_max_hunger(self, ctx, max_hunger: int) -> str:
        """Set the max Hunger rating to 5 or 10."""
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set the max Hunger rating.")

        vguild = await self.find_guild(ctx.guild)
        vguild.settings.max_hunger = max_hunger
        await vguild.save_changes()

        return f"Max Hunger rating is now `{max_hunger}`."

    # Cache management

    async def find_guild(self, guild: discord.Guild | int | None) -> VGuild:
        """Fetches a guild from the database or creates it if not found."""
        if guild is None:
            # We're in DMs
            return VGuild(id=0, name="DM")

        guild_id = guild if isinstance(guild, int) else guild.id
        if vguild := self._guild_cache.get(guild_id):
            return vguild

        # Guild not in cache
        vguild = await VGuild.find_one(VGuild.guild == guild_id)
        if vguild is None:
            # Guild doesn't exist!
            vguild = VGuild.from_guild(guild)
            await vguild.insert()

        self._guild_cache[guild_id] = vguild
        return vguild

    async def find_user(self, user: discord.User | int) -> VUser:
        """Fetches a user from the database or creates it if not found."""
        user_id = user if isinstance(user, int) else user.id

        if user := self._user_cache.get(user_id):
            return user

        # User not in cache
        user = await VUser.find_one(VUser.user == user_id)
        if user is None:
            # User not in the database
            user = VUser(user=user_id)
            await user.insert()

        self._user_cache[user_id] = user
        return user
