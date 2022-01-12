"""stats.py - Various packages for user statistics."""

import datetime
import os

import pymongo


class Stats:
    """Roll outcome logging."""
    _CLIENT = None
    _STATS = None
    _GUILDS = None


    @classmethod
    def log_roll(cls, guild: int, user: int, char, outcome, comment):
        """
        Log a roll and its outcome. If the roll is a reroll, simply replace it.
        Args:
            guild (int): The Discord ID of the guild where the roll was made
            user (int): The Discord ID of the user making the roll
            charid (VChar): The character that made the roll (optional)
            outcome (Roll): The roll's parameters and outcome
        """
        Stats.__prepare()

        if Stats._STATS.find_one({ "_id": outcome.id }) is None:
            Stats.__add_roll(guild, user, char, outcome, comment)
        else:
            Stats.__update_roll(outcome)


    @classmethod
    def guild_joined(cls, guild, name):
        """
        Log whenever a guild is joined.
        Args:
            guild (int): The guild's Discord ID
            name (str): The guild's name
        """
        Stats.__prepare()

        if Stats._GUILDS.find_one({ "guild": guild }) is None:
            Stats._GUILDS.insert_one({
                "guild": guild,
                "name": name,
                "active": True,
                "joined": datetime.datetime.utcnow(),
                "left": None
            })
        else:
            Stats._GUILDS.update_one({ "guild": guild }, {
                "$set": {
                    "name": name, # The guild may have been renamed in the interim, so set the name
                    "active": True,
                    "joined": datetime.datetime.utcnow(), # Re-joined date
                    "left": None
                }
            })


    @classmethod
    def guild_left(cls, guild):
        """
        Log whenever a guild is deleted or Inconnu is kicked from a guild.
        Args:
            guild (int): The guild's Discord ID
        """
        Stats.__prepare()

        Stats._GUILDS.update_one({ "guild": guild }, {
            "$set": {
                "active": False,
                "left": datetime.datetime.utcnow()
            }
        })


    @classmethod
    def guild_renamed(cls, guild, new_name):
        """
        Log guild renames.
        Args:
            guild (int): The guild's Discord ID
            name (str): The guild's name
        """
        Stats.__prepare()
        Stats._GUILDS.update_one({ "guild": guild }, { "$set": { "name": new_name } })


    # Roll logging helpers

    @classmethod
    def __add_roll(cls, guild: int, user: int, char, outcome, comment):
        """Add a new roll outcome entry to the database."""
        Stats._STATS.insert_one({
            "_id": outcome.id,
            "date": datetime.datetime.utcnow(),
            "guild": guild, # We use the guild and user keys for easier lookups
            "user": user,
            "charid": char.id if char is not None else None,
            "raw": outcome.syntax,
            "normal": outcome.normal.dice,
            "hunger": outcome.hunger.dice,
            "difficulty": outcome.difficulty,
            "margin": outcome.margin,
            "outcome": outcome.outcome,
            "pool": outcome.pool_str,
            "comment": comment,
            "reroll": None,
        })


    @classmethod
    def __update_roll(cls, outcome):
        """
        Update a roll entry.
        Args:
            ident (ObjectId): The entry's identifier
            outcome (Roll): The new outcome
        """
        Stats._STATS.update_one({ "_id": outcome.id }, {
            "$set": {
                "reroll": {
                    "strategy": outcome.strategy,
                    "dice": outcome.normal.dice,
                    "margin": outcome.margin,
                    "outcome": outcome.outcome
                }
            }
        })


    @classmethod
    def __prepare(cls):
        """Prepare the database."""
        try:
            Stats._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            Stats._CLIENT = None
        finally:
            if Stats._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Stats._CLIENT = mongo
                Stats._STATS = mongo.inconnu.rolls
                Stats._GUILDS = mongo.inconnu.guilds
