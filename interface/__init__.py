"""Miscellaneous shared interface functions."""

from typing import Any, Awaitable, Callable

from pymongo import DeleteOne, UpdateOne

from logger import Logger


async def raw_message_delete_handler(
    raw_message, bot, handler: Callable[[int], Awaitable], author_comparator=None
):
    """Handle raw message deletion."""
    comparator = author_comparator or (lambda author: author == bot.user)

    # We only have a raw message event, which may not be in the message
    # cache. If it isn't, then we just have to blindly attempt to remove
    # the record.
    if (message := raw_message.cached_message) is not None:
        if message.flags.ephemeral:
            Logger.debug("RAW DELETER: Ignoring ephemeral message")
            return
        # Got a cached message, so we can be a little more efficient and
        # only call the database if it belongs to the bot
        if comparator(message.author):
            Logger.debug("RAW DELETER: Handling bot message")
            await handler(message.id)
    else:
        # The message isn't in the cache; blindly delete the record
        # if it exists
        Logger.debug("RAW DELETER: Blindly handling potential bot message")
        await handler(raw_message.message_id)


def raw_bulk_delete_handler(
    payload, bot, gen_update: Callable[[int], DeleteOne | UpdateOne], author_comparator=None
):
    """Handle bulk message deletion."""
    comparator = author_comparator or (lambda author: author == bot.user)
    raw_ids = payload.message_ids
    write_ops = []

    for message in payload.cached_messages:
        if message.flags.ephemeral:
            Logger.debug("RAW BULK HANDLER: Ignoring ephemeral message")
            continue

        raw_ids.discard(message.id)  # Prevent double updates

        if comparator(message.author):
            Logger.debug("RAW BULK DELETER: Adding potential bot message to queue")
            write_ops.append(gen_update(message.id))

    for message_id in raw_ids:
        Logger.debug("RAW BULK DELETER: Blindly adding potential bot message to queue")
        write_ops.append(gen_update(message_id))

    return write_ops
