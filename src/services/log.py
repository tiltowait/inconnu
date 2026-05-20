"""log.py - Database error reporting."""

import textwrap

import discord

from config import settings


async def report_database_error(bot, ctx):
    """Report an error to the appropriate channel."""
    errmsg = """\
    My database is down. Some features are unavailable.
    This error has been reported. Please try again in a bit!"""
    await ctx.respond(textwrap.dedent(errmsg), ephemeral=True)

    # Send an error message to the support server
    if settings.db_error_channel is not None:
        timestamp = discord.utils.format_dt(discord.utils.utcnow())
        channel = bot.get_channel(settings.db_error_channel)
        await channel.send(f"{timestamp}: Database error detected.")
