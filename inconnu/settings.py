"""settings.py - User- and server-wide settings."""

import os
from enum import Enum

import discord
import pymongo


class ExpPerms(str, Enum):
    """An enum for experience adjustment permissions."""

    UNRESTRICTED = "unrestricted"
    UNSPENT_ONLY = "unspent_only"
    LIFETIME_ONLY = "lifetime_only"
    ADMIN_ONLY = "admin_only"


class Settings:
    """A class for managing individual and server-wide settings."""

    # Collections
    _CLIENT = None
    _GUILDS = None
    _USERS = None


    @classmethod
    def accessible(cls, user):
        """Determine whether we should use accessibility mode."""
        Settings._prepare()

        if isinstance(user, discord.Member):
            guildwide = Settings._GUILDS.find_one({
                "guild": user.guild.id,
                "settings.accessibility": True
            })
            if guildwide is not None:
                return True

        userwide = Settings._USERS.find_one({
            "user": user.id,
            "settings.accessibility": True
        })
        return userwide is not None


    @classmethod
    def set_accessibility(cls, ctx, enabled: bool, scope: str):
        """
        Set the accessibility mode.
        Args:
            ctx: Discord context
            enabled (bool): The accessibility toggle
            scope (str): "user" or "server"
        """
        if scope == "user":
            Settings._set_key(ctx.user, "accessibility", enabled)

            if enabled:
                response = "**Accessibility mode** enabled."
            else:
                response = "**Accessibility mode** disabled. Note: the server may override."
        else: # Server-wide setting
            if not ctx.user.guild_permissions.administrator:
                raise PermissionError("Sorry, only admins can set server-wide accessibility mode.")

            Settings._set_key(ctx.guild, "accessibility", enabled)

            if enabled:
                response = "**Accessibility mode** enabled server-wide."
            else:
                response = "**Accessibility mode** disabled server-wide. Users may override."

        return response


    @classmethod
    def can_adjust_current_xp(cls, ctx) -> bool:
        """Whether the user can adjust their current XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        try:
            guild = Settings._fetch_guild(ctx.guild)
            permissions = guild["settings"]["experience_permissions"]
            permissions = ExpPerms(permissions)

            return permissions in [ExpPerms.UNRESTRICTED, ExpPerms.UNSPENT_ONLY]
        except KeyError:
            # If there are no settings, default to unrestricted
            return True


    @classmethod
    def can_adjust_lifetime_xp(cls, ctx) -> bool:
        """Whether the user has permission to adjust lifetime XP."""
        if ctx.user.guild_permissions.administrator:
            return True

        try:
            guild = Settings._fetch_guild(ctx.guild)
            permissions = guild["settings"]["experience_permissions"]
            permissions = ExpPerms(permissions)

            return permissions in [ExpPerms.UNRESTRICTED, ExpPerms.LIFETIME_ONLY]
        except KeyError:
            # If there are no settings, default to unrestricted
            return True


    @classmethod
    def xp_permissions(cls, guild):
        """Get the XP permissions."""
        try:
            guild = Settings._fetch_guild(guild)
            permissions = ExpPerms(guild["settings"]["experience_permissions"])
        except KeyError:
            permissions = ExpPerms.UNRESTRICTED

        match permissions:
            case ExpPerms.UNRESTRICTED:
                return "Users may adjust unspent and lifetime XP."
            case ExpPerms.UNSPENT_ONLY:
                return "Users may adjust unspent XP only."
            case ExpPerms.LIFETIME_ONLY:
                return "Users may adjust lifetime XP only."
            case ExpPerms.ADMIN_ONLY:
                return "Only admins may adjust XP totals."


    @classmethod
    def set_xp_permissions(cls, ctx, permissions):
        """
        Set the XP settings:
            • User can modify current and lifetime
            • User can modify current
            • User can modify lifetime
            • User can't modify any
        """
        if not ctx.user.guild_permissions.administrator:
            raise PermissionError("Sorry, only admins can set user experience permissions.")

        Settings._set_key(ctx.guild, "experience_permissions", permissions)

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



    @classmethod
    def oblivion_stains(cls, guild) -> list:
        """Retrieve the Rouse results that grant Oblivion stains."""
        try:
            guild = Settings._fetch_guild(guild)
            oblivion = guild["settings"]["oblivion_stains"]
        except KeyError:
            oblivion = [1, 10]

        return oblivion


    @classmethod
    def set_oblivion_stains(cls, ctx, stains: int):
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

        Settings._set_key(ctx.guild, "oblivion_stains", stains)
        return response


    @classmethod
    def _set_key(cls, scope, key: str, value):
        """
        Enable or disable a setting.
        Args:
            scope (discord.Guild | discord.Member): user or guild
            key (str): The setting key
            value: The value to set
        """
        Settings._prepare()

        if isinstance(scope, discord.Guild):
            Settings._set_guild(scope, key, value)
        elif isinstance(scope, discord.Member):
            Settings._set_user(scope, key, value)
        else:
            return ValueError(f"Unknown scope `{scope}`.")

        return True


    @classmethod
    def _set_guild(cls, guild: discord.Guild, key:str, value):
        """Enable or disable a guild setting."""
        res = Settings._GUILDS.update_one({ "guild": guild.id }, {
            "$set": {
                f"settings.{key}": value
            }
        })
        if res.matched_count == 0:
            Settings._GUILDS.insert_one({ "guild": guild.id, "settings": { key: value } })


    @classmethod
    def _set_user(cls, user: discord.Member, key:str, value):
        """Enable or disable a user setting."""
        res = Settings._USERS.update_one({ "user": user.id }, {
            "$set": {
                f"settings.{key}": value
            }
        })
        if res.matched_count == 0:
            Settings._USERS.insert_one({ "user": user.id, "settings": { key: value } })


    @classmethod
    def _fetch_guild(cls, guild):
        """Fetch a guild."""
        Settings._prepare()

        if not isinstance(guild, int):
            guild = guild.id

        return Settings._GUILDS.find_one({"guild": guild })


    @classmethod
    def _prepare(cls):
        """Prepare the database."""
        try:
            Settings._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            Settings._CLIENT = None
        finally:
            if Settings._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Settings._CLIENT = mongo
                Settings._GUILDS = mongo.inconnu.guilds
                Settings._USERS = mongo.inconnu.users
