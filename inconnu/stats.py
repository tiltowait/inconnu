"""stats.py - Various packages for user statistics."""

import os

import pymongo


class Stats:
    """Roll outcome logging."""
    _CLIENT = None
    _STATS = None


    @classmethod
    def log_roll(cls, guild: int, user: int, char, outcome):
        """
        Log a roll and its outcome. If the roll is a reroll, simply replace it.
        Args:
            guild (int): The Discord ID of the guild where the roll was made
            user (int): The Discord ID of the user making the roll
            charid (VChar): The character that made the roll (optional)
            outcome (RollResult): The roll's parameters and outcome
        """
        Stats.__prepare()

        if Stats._STATS.find_one({ "_id": outcome.id }) is None:
            Stats.__add_roll(guild, user, char, outcome)
        else:
            Stats.__update_roll(outcome)


    @classmethod
    def __add_roll(cls, guild: int, user: int, char, outcome):
        """Add a new roll outcome entry to the database."""
        Stats._STATS.insert_one({
            "_id": outcome.id,
            "guild": guild, # We use the guild and user keys for easier lookups
            "user": user,
            "charid": char.id if char is not None else None,
            "normal": outcome.normal.dice,
            "hunger": outcome.hunger.dice,
            "difficulty": outcome.difficulty,
            "margin": outcome.margin,
            "outcome": outcome.outcome,
            "pool": outcome.pool_str,
            "reroll": None,
        })


    @classmethod
    def __update_roll(cls, outcome):
        """
        Update a roll entry.
        Args:
            ident (ObjectId): The entry's identifier
            outcome (RollResult): The new outcome
        """
        Stats._STATS.update_one({ "_id": outcome.id }, {
            "$set": {
                "normal": outcome.normal.dice,
                "margin": outcome.margin,
                "outcome": outcome.outcome,
                "reroll": outcome.reroll
            }
        })



    @classmethod
    def __prepare(cls):
        """Prepare the database."""
        try:
            Stats._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            print("Establishing MongoDB connection.")
            Stats._CLIENT = None
        finally:
            if Stats._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Stats._CLIENT = mongo
                Stats._STATS = mongo.inconnu.statistics
