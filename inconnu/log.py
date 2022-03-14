"""log.py - Logging facilities."""
# pylint: disable=too-few-public-methods

import datetime
import os
import textwrap
import traceback

import discord

import inconnu


async def log_event(event_key, **context):
    """Log a bot event."""
    log = inconnu.db.log

    if event_key in ["update", "update_error", "roll_error", "macro_update_error"]:
        await log.insert_one({
            "date": datetime.datetime.utcnow(),
            "event": event_key,
            "context": context
        })
    else:
        raise KeyError("Invalid event key:", event_key)


async def report_database_error(bot, ctx):
    """Report an error to the appropriate channel."""
    errmsg = """\
    My database is down. Some features are unavailable.
    This error has been reported. Please try again in a bit!"""
    await inconnu.respond(ctx)(textwrap.dedent(errmsg), ephemeral=True)

    # Send an error message to the support server
    if (db_error_channel := os.getenv("DB_ERROR_CHANNEL")) is not None:
        timestamp = inconnu.gen_timestamp(discord.utils.utcnow())

        db_error_channel = bot.get_channel(int(db_error_channel))
        await db_error_channel.send(f"{timestamp}: Database error detected.")


async def report_error(bot, ctx, error):
    """Report an error to the appropriate channel."""
    if (channel := os.getenv("REPORT_CHANNEL")) is None:
        raise error

    embed = discord.Embed(
        title=type(error).__name__,
        description="\n".join(traceback.format_exception(error)),
        color=0xff0000,
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(
        name=f"{ctx.user.name} on {ctx.guild.name}",
        icon_url=ctx.guild.icon or ""
    )

    channel = bot.get_channel(int(channel))
    await channel.send(embed=embed)
