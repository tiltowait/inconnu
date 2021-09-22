"""settings.py - User- and server-wide settings."""

import os

import discord
import pymongo


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
    def set_key(cls, scope, key: str, enabled: bool):
        """
        Enable or disable a setting.
        Args:
            scope (str): "user" or "guild"
            key (str): The setting key
            enabled (bool): Enable or disable
        """
        Settings._prepare()

        if isinstance(scope, discord.Guild):
            raise ValueError("Guild settings not yet implemented.")
        elif isinstance(scope, discord.Member):
            Settings._set_user(scope, key, enabled)
        else:
            return ValueError(f"Unknown scope `{scope}`.")

        return True


    @classmethod
    def _set_user(cls, user: discord.Member, key:str, enabled: bool):
        """Enable or disable a user setting."""
        res = Settings._USERS.update_one({ "user": user.id }, {
            "$set": {
                f"settings.{key}": enabled
            }
        })
        if res.matched_count == 0:
            Settings._USERS.insert_one({ "user": user.id, "settings": { key: enabled } })


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
