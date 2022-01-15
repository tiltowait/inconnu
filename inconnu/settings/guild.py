"""settings/guild.py - Guild-specific settings."""

import os

import pymongo


class Guild:
    """Various setters and getters for server-wide settings."""

    _CLIENT = None
    _GUILDS = None


    def __init__(self, guild):
        Guild._prepare()

        self._params = Guild._GUILDS.find_one({ "guild": guild })
        self.id = self._params["guild"] # pylint: disable=invalid-name


    @property
    def accessible(self) -> bool:
        """Whether the server uses accessibility mode."""
        return self._params.get("settings", {}).get("accessibility", False)


    @accessible.setter
    def accessible(self, accessibility):
        """Set the server's accessibility mode."""
        self._set("accessibility", accessibility)


    @property
    def oblivion_stains(self) -> list:
        """The Rouse results that can give stains on Oblivion rolls."""
        return self._params.get("settings", {}).get("oblivion_stains", [1, 10])


    @oblivion_stains.setter
    def oblivion_stains(self, stains):
        """Set the server's Oblivion rouse result stains."""
        self._set("oblivion_stains", stains)


    @property
    def admin_role(self):
        """Retrieve server's admin role."""
        return self._params.get("settings", {}).get("admin_role", None)


    @admin_role.setter
    def admin_role(self, role):
        """Set the server's admin role."""
        if not isinstance(role, int):
            role = role.id

        self._set("admin_role", role)


    def _set(self, key, value):
        """Set a given settings key to a given value."""
        Guild._GUILDS.update_one({ "guild": self.id }, {
            "$set": {
                f"settings.{key}": value
            }
        })


    @classmethod
    def _prepare(cls):
        """Prepare the database."""
        try:
            Guild._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            Guild._CLIENT = None
        finally:
            if Guild._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Guild._CLIENT = mongo
                Guild._GUILDS = mongo.inconnu.guilds
