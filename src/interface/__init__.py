"""Miscellaneous shared interface functions."""

from typing import Awaitable, Callable

from loguru import logger
from pymongo import DeleteOne, UpdateOne


def _no_author_match(_):
    """Default author comparator that always returns False."""
    return False


async def raw_message_delete_handler(
    raw_message, bot, handler: Callable[[int], Awaitable], author_comparator=None
):
    """Handle raw message deletion."""
    if author_comparator is None:
        author_comparator = _no_author_match

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
    payload, bot, gen_update: Callable[[int], DeleteOne | UpdateOne], author_comparator=None
):
    """Handle bulk message deletion."""
    if author_comparator is None:
        author_comparator = _no_author_match

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
