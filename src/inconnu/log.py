"""log.py - Logging facilities."""
# pylint: disable=too-few-public-methods

import os
import textwrap
from datetime import UTC, datetime

import discord

import inconnu


async def log_event(event_key, **context):
    """Log a bot event."""
    log = inconnu.db.log

    if event_key in ["update", "update_error", "roll_error", "macro_update_error"]:
        await log.insert_one(
            {"date": datetime.now(UTC), "event": event_key, "context": context}
        )
    else:
        raise KeyError("Invalid event key:", event_key)


async def report_database_error(bot, ctx):
    """Report an error to the appropriate channel."""
    errmsg = """\
    My database is down. Some features are unavailable.
    This error has been reported. Please try again in a bit!"""
    await ctx.respond(textwrap.dedent(errmsg), ephemeral=True)

    # Send an error message to the support server
    if (db_error_channel := os.getenv("DB_ERROR_CHANNEL")) is not None:
        timestamp = discord.utils.format_dt(discord.utils.utcnow())

        db_error_channel = bot.get_channel(int(db_error_channel))
        await db_error_channel.send(f"{timestamp}: Database error detected.")
