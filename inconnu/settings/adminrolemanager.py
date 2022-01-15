"""settings/adminrolemanager.py - Utility for informing cogs that guild roles have changed."""

import os

import pymongo

from .guild import Guild


class AdminRoleManager:
    """A class that informs delegates of guild admin role changes."""

    def __init__(self):
        self.client = None
        self.guild_col = None

        self._prepare()

        self.observers = []


    async def load_admin_roles(self):
        """Load the persisted state."""
        guilds = self.guild_col.find({ "active": True })
        guilds = map(lambda guild: Guild(guild["guild"]), guilds)

        for guild in guilds:
            if guild.admin_role is not None:
                await self.assign_role(guild.admin_role, guild.id)


    def add_observer(self, observer):
        """Add a cog to the observer list."""
        self.observers.append(observer)


    async def assign_role(self, role: int, guild: int):
        """Inform all observers of an admin role change."""
        if not isinstance(role, int):
            role = role.id
        if not isinstance(guild, int):
            guild = guild.id

        for observer in self.observers:
            await observer.admin_role_changed(role, guild)


    def _prepare(self):
        """Prepare the database connection."""
        try:
            self.client.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            self.client = None
        finally:
            if self.client is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                self.client = mongo
                self.guild_col = mongo.inconnu.guilds
