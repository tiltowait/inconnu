"""stats.py - Various packages for user statistics."""
# pylint: disable=too-many-arguments

import datetime
from typing import Optional

from pymongo import ReturnDocument

import inconnu


async def log_roll(guild: int, user: int, message: int, char, outcome, comment):
    """
    Log a roll and its outcome. If the roll is a reroll, simply replace it.
    Args:
        guild (int): The Discord ID of the guild where the roll was made
        user (int): The Discord ID of the user making the roll
        charid (VChar): The character that made the roll (optional)
        outcome (Roll): The roll's parameters and outcome
    """
    rolls = inconnu.db.rolls

    if await rolls.find_one({"_id": outcome.id}) is None:
        roll = _gen_roll(guild, user, message, char, outcome, comment)
        await rolls.insert_one(roll)
    else:
        reroll = _gen_reroll(outcome)
        await rolls.update_one({"_id": outcome.id}, reroll)


async def toggle_roll_stats(message: int) -> bool:
    """Toggle whether a roll should be used in statistics."""
    ret = await inconnu.db.rolls.find_one_and_update(
        {"message": message},
        [{"$set": {"use_in_stats": {"$not": "$use_in_stats"}}}],
        return_document=ReturnDocument.AFTER,
    )

    if ret:
        return ret["use_in_stats"]
    return None


async def roll_message_deleted(message: int):
    """Remove a roll from stats calculation."""
    await inconnu.db.rolls.update_one({"message": message}, {"$set": {"use_in_stats": False}})


async def guild_joined(guild):
    """
    Log whenever a guild is joined.
    Args:
        guild (int): The guild's Discord ID
        name (str): The guild's name
    """
    guilds = inconnu.db.guilds

    await guilds.update_one(
        {"guild": guild.id},
        {
            "$set": {
                "guild": guild.id,
                "name": guild.name,
                "active": True,
                "joined": datetime.datetime.utcnow(),
                "left": None,
            }
        },
        upsert=True,
    )


async def guild_left(guild):
    """
    Log whenever a guild is deleted or Inconnu is kicked from a guild.
    Args:
        guild (int): The guild's Discord ID
    """
    guilds = inconnu.db.guilds

    await guilds.update_one(
        {"guild": guild}, {"$set": {"active": False, "left": datetime.datetime.utcnow()}}
    )


async def guild_renamed(guild, new_name):
    """
    Log guild renames.
    Args:
        guild (int): The guild's Discord ID
        name (str): The guild's name
    """
    guilds = inconnu.db.guilds

    await guilds.update_one({"guild": guild}, {"$set": {"name": new_name}})


# Roll logging helpers


def _gen_roll(guild: int, user: int, message: int, char, outcome, comment: str):
    """Add a new roll outcome entry to the database."""
    return {
        "_id": outcome.id,
        "date": datetime.datetime.utcnow(),
        "guild": guild,  # We use the guild and user keys for easier lookups
        "user": user,
        "message": message,
        "charid": getattr(char, "object_id", None),
        "raw": outcome.syntax,
        "normal": outcome.normal.dice,
        "hunger": outcome.hunger.dice,
        "difficulty": outcome.difficulty,
        "margin": outcome.margin,
        "outcome": outcome.outcome,
        "pool": outcome.pool_str,
        "comment": comment,
        "reroll": None,
        "use_in_stats": True,
    }


def _gen_reroll(outcome):
    """
    Update a roll entry.
    Args:
        ident (ObjectId): The entry's identifier
        outcome (Roll): The new outcome
    """
    return {
        "$set": {
            "reroll": {
                "strategy": outcome.strategy,
                "dice": outcome.normal.dice,
                "margin": outcome.margin,
                "outcome": outcome.outcome,
            }
        },
    }
