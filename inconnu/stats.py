"""stats.py - Various packages for user statistics."""
# pylint: disable=too-many-arguments

import datetime

import discord

import inconnu


async def log_roll(guild: int, user: int, char, outcome, comment):
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
        roll = _gen_roll(guild, user, char, outcome, comment)
        await rolls.insert_one(roll)
    else:
        reroll = _gen_reroll(outcome)
        await rolls.update_one({"_id": outcome.id}, reroll)


async def guild_joined(guild: discord.Guild):
    """
    Log whenever a guild is joined.
    Args:
        guild (int): The guild's Discord ID
        name (str): The guild's name
    """
    # We are upserting, so we don't use commit()
    if old_guild := await inconnu.Guild.find_one({"guild": guild.id}):
        old_guild.active = True
        old_guild.left = None
    else:
        guild = inconnu.Guild(guild=guild.id, name=guild.name)
        await guild.commit()


async def guild_left(guild: discord.Guild):
    """
    Log whenever a guild is deleted or Inconnu is kicked from a guild.
    Args:
        guild (int): The guild's Discord ID
    """
    guild = await inconnu.Guild.find_one({"guild": guild.id})
    guild.active = False
    guild.left = datetime.datetime.utcnow()
    await guild.commit()


async def guild_renamed(guild, new_name):
    """
    Log guild renames.
    Args:
        guild (int): The guild's Discord ID
        name (str): The guild's name
    """
    guild = await inconnu.Guild.find_one({"guild": guild.id})
    guild.name = new_name
    await guild.commit()


# Roll logging helpers


def _gen_roll(guild: int, user: int, char, outcome, comment):
    """Add a new roll outcome entry to the database."""
    return {
        "_id": outcome.id,
        "date": datetime.datetime.utcnow(),
        "guild": guild,  # We use the guild and user keys for easier lookups
        "user": user,
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
        }
    }
