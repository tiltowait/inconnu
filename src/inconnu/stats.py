"""stats.py - Various packages for user statistics."""

from datetime import UTC, datetime

import discord
from pymongo import ReturnDocument, UpdateOne

import db
import inconnu
from models import VChar
from models import VGuild


async def log_roll(
    guild: int,
    channel: int,
    user: int,
    message: int | None,
    char: VChar | None,
    outcome,
    comment,
):
    """
    Log a roll and its outcome. If the roll is a reroll, simply replace it.
    Args:
        guild (int): The Discord ID of the guild where the roll was made
        user (int): The Discord ID of the user making the roll
        charid (VChar): The character that made the roll (optional)
        outcome (Roll): The roll's parameters and outcome
    """
    rolls = db.rolls

    if await rolls.find_one({"_id": outcome.id}) is None:
        roll = _gen_roll(guild, channel, user, message, char, outcome, comment)
        await rolls.insert_one(roll)
    else:
        reroll = _gen_reroll(outcome)
        await rolls.update_one({"_id": outcome.id}, reroll)


async def toggle_roll_stats(message: int) -> bool | None:
    """Toggle whether a roll should be used in statistics."""
    ret = await db.rolls.find_one_and_update(
        {"message": message},
        [{"$set": {"use_in_stats": {"$not": "$use_in_stats"}}}],
        return_document=ReturnDocument.AFTER,
    )

    if ret:
        return ret["use_in_stats"]
    return None


async def roll_message_deleted(*message_ids):
    """Remove a set of rolls from stats calculation."""
    updates = []
    for message_id in message_ids:
        updates.append(UpdateOne({"message": message_id}, {"$set": {"use_in_stats": False}}))

    await db.rolls.bulk_write(updates)


async def delete_rolls_in_channel(channel):
    """Delete all rolls in a channel."""
    await db.rolls.update_many({"channel": channel.id}, {"$set": {"use_in_stats": False}})


async def guild_joined(guild: discord.Guild):
    """Log whenever a guild is joined."""
    vguild = await VGuild.get_or_fetch(guild)
    vguild.join()

    await vguild.save()


async def guild_left(guild: discord.Guild):
    """Log whenever a guild is deleted or Inconnu is kicked from a guild."""
    vguild = await VGuild.get_or_fetch(guild)
    vguild.leave()

    await vguild.save()


async def guild_renamed(guild: discord.Guild, new_name: str):
    """Log guild renames."""
    vguild = await VGuild.get_or_fetch(guild)
    vguild.name = new_name

    await vguild.save()


# Roll logging helpers


def _gen_roll(
    guild: int,
    channel: int,
    user: int,
    message: int | None,
    char: VChar | None,
    outcome,
    comment: str,
):
    """Add a new roll outcome entry to the database."""
    return {
        "_id": outcome.id,
        "date": datetime.now(UTC),
        "guild": guild,  # We use the guild and user keys for easier lookups
        "channel": channel,
        "user": user,
        "message": message,
        "charid": getattr(char, "id", None),
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
