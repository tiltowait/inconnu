"""Discord command and interaction helpers."""

from typing import TYPE_CHECKING, Any, Awaitable, Callable

import discord
from discord.ext.commands import Paginator
from loguru import logger
from pymongo import DeleteOne, UpdateOne

if TYPE_CHECKING:
    from bot import InconnuBot


def raw_command_options(interaction) -> dict[str, Any]:
    """Get the options in a command as a dict."""
    options = {}
    for option in interaction.data.get("options", []):
        name = option["name"]
        value = option["value"]
        options[name] = value

    return options


def command_options(interaction) -> str:
    """Format the command options for easy display."""
    options = []
    for option in interaction.data.get("options", []):
        _name = option["name"]
        _value = option["value"]

        # This is hardly exhaustive, since option types can also be members
        # or channels, but the main purpose with enclosing strings in quotes
        # is to remove ambiguity that might occur with more complex string
        # patterns.
        if isinstance(_value, str):
            options.append(f'{_name}="{_value}"')
        else:
            options.append(f"{_name}={_value}")

    return ", ".join(options) if options else "None"


def re_paginate(strings: list[str], *, page_len=2000) -> list[str]:
    """Adjusts the pages into the fewest number of <=2k pages possible.
    It does so via three possible methods:
      1. Newlines
      2. Spaces
      3. Individual characters
    """
    delimiter = ""
    for i in range(1, len(strings) * 2, 2):
        # Insert a newline between each page to make sure paragraphs are
        # properly broken. It's fine if the last element ends up being a
        # newline; it will be removed later.
        strings.insert(i, delimiter)

    # Default case: paginate by newlines
    lines = sum([string.split("\n") for string in strings], [])
    paginator = Paginator(prefix="", suffix="", max_size=page_len)

    try:
        for line in lines:
            paginator.add_line(line)
        return [page.strip() for page in paginator.pages]
    except RuntimeError:
        pass

    # Newlines failed; split by words
    words = sum([string.split(" ") for string in strings], [])
    paginator = Paginator(prefix="", suffix="", linesep=" ", max_size=page_len)

    try:
        for word in words:
            paginator.add_line(word)
        return [page.strip() for page in paginator.pages]
    except RuntimeError:
        pass

    # Spaces failed; split by characters
    combined = "".join(strings)
    return [combined[i : i + page_len].strip() for i in range(0, len(combined), page_len)]


async def get_message(inter):
    """Get the message from an interaction."""
    if isinstance(inter, discord.Message):
        return inter
    return await inter.original_response()


def get_avatar(user: discord.User | discord.Member) -> discord.Asset:
    """Get the user's avatar."""
    if isinstance(user, discord.User):
        # Users don't have a guild presence
        return user.display_avatar

    # Members can have a guild-specific avatar
    return user.guild_avatar or user.display_avatar


def _no_author_match(_):
    """Default author comparator that always returns False."""
    return False


async def raw_message_delete_handler(
    raw_message: discord.RawMessageDeleteEvent,
    bot: "InconnuBot",
    handler: Callable[[int], Awaitable],
    author_comparator=_no_author_match,
):
    """Handle raw message deletion."""
    # We only have a raw message event, which may not be in the message
    # cache. If it isn't, then we just have to blindly attempt to remove
    # the record.
    if (message := raw_message.cached_message) is not None:
        if message.flags.ephemeral:
            logger.debug("RAW DELETER: Ignoring ephemeral message")
            return
        # Got a cached message, so we can be a little more efficient and
        # only call the database if it belongs to the bot
        if author_comparator(message.author) or message.author == bot.user:
            logger.debug("RAW DELETER: Handling bot message")
            await handler(message.id)
    else:
        # The message isn't in the cache; blindly delete the record
        # if it exists
        logger.debug("RAW DELETER: Blindly handling potential bot message")
        await handler(raw_message.message_id)


def raw_bulk_delete_handler(
    payload: discord.RawBulkMessageDeleteEvent,
    bot: "InconnuBot",
    gen_update: Callable[[int], DeleteOne | UpdateOne | int],
    author_comparator=_no_author_match,
):
    """Handle bulk message deletion."""
    raw_ids = payload.message_ids
    write_ops = []

    for message in payload.cached_messages:
        if message.flags.ephemeral:
            logger.debug("RAW BULK HANDLER: Ignoring ephemeral message")
            continue

        raw_ids.discard(message.id)  # Prevent double updates

        if author_comparator(message.author) or message.author == bot.user:
            logger.debug("RAW BULK DELETER: Adding potential bot message to queue")
            write_ops.append(gen_update(message.id))

    for message_id in raw_ids:
        logger.debug("RAW BULK DELETER: Blindly adding potential bot message to queue")
        write_ops.append(gen_update(message_id))

    return write_ops


async def player_lookup(ctx, player: discord.Member | None):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player_str is None.

    Raises PermissionError if the user doesn't have admin permissions.
    Raises ValueError if player is not a valid player name.
    """
    if player is None:
        return ctx.user

    # Players are allowed to look up themselves
    if (not ctx.user.guild_permissions.administrator) and ctx.user != player:
        raise LookupError("You don't have lookup permissions.")

    return player
