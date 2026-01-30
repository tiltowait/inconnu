"""log.py - Database error reporting."""

import os
import textwrap

import discord


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
