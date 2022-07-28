"""Bot instance and event handlers."""

import asyncio
import os
from datetime import time, timezone

import discord
import topgg
from discord.ext import tasks

import config.logging
import inconnu
import s3
from errorreporter import reporter
from logger import Logger

# Check if we're in dev mode
if (_debug_guilds := os.getenv("DEBUG")) is not None:
    debug_guilds = [int(g) for g in _debug_guilds.split(",")]
    Logger.info("MAIN: Debugging on %s", debug_guilds)
else:
    debug_guilds = None


class InconnuBot(discord.Bot):
    """Adds minor functionality over the superclass. All commands in cogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.welcomed = False
        Logger.info("BOT: Instantiated")


# Set up the bot instance
intents = discord.Intents(guilds=True, members=True, messages=True)
bot = InconnuBot(intents=intents, debug_guilds=debug_guilds)

# General Events


@bot.event
async def on_ready():
    """Schedule a task to perform final setup."""
    await __set_presence()
    task = bot.loop.create_task(finish_setup())
    await task


async def finish_setup():
    """Print login message and perform final setup."""
    if bot.welcomed:
        return

    await bot.wait_until_ready()
    bot.welcomed = True

    Logger.info("BOT: Logged in as %s!", str(bot.user))
    Logger.info("BOT: Playing on %s servers", len(bot.guilds))
    Logger.info("BOT: %s", discord.version_info)
    Logger.info("BOT: Latency: %s ms", bot.latency * 1000)

    await inconnu.emojis.load(bot)
    server_info = await inconnu.db.server_info()
    database = os.environ["MONGO_DB"]
    Logger.info("MONGO: Version %s, using %s database", server_info["version"], database)

    # Schedule tasks
    cull_inactive.start()
    upload_logs.start()

    # Final prep
    inconnu.char_mgr.bot = bot
    reporter.prepare_channel(bot)
    Logger.info("BOT: Ready")


@bot.event
async def on_application_command_error(ctx, error):
    """Use centralized reporter to handle errors."""
    await reporter.report_error(ctx, error)


# Member Events


@bot.event
async def on_member_remove(member):
    """Mark all of a member's characters as inactive."""
    await inconnu.char_mgr.mark_inactive(member)


@bot.event
async def on_member_join(member):
    """Mark all the player's characters as active when they rejoin a guild."""
    await inconnu.char_mgr.mark_active(member)


# Guild Events


@bot.event
async def on_guild_join(guild):
    """Log whenever a guild is joined."""
    Logger.info("BOT: Joined %s!", guild.name)
    await asyncio.gather(inconnu.stats.guild_joined(guild), __set_presence())


@bot.event
async def on_guild_remove(guild):
    """Log guild removals."""
    Logger.info("BOT: Left %s :(", guild.name)
    await asyncio.gather(inconnu.stats.guild_left(guild.id), __set_presence())


@bot.event
async def on_guild_update(before, after):
    """Log guild name changes."""
    if before.name != after.name:
        Logger.info("BOT: Renamed %s => %s", before.name, after.name)
        await inconnu.stats.guild_renamed(after.id, after.name)


# Tasks


@tasks.loop(time=time(12, 0, tzinfo=timezone.utc))
async def cull_inactive():
    """Cull inactive characters and guilds."""
    await inconnu.culler.cull()


@tasks.loop(hours=1)
async def upload_logs():
    """Upload logs to S3."""
    if not config.logging.upload_to_aws:
        Logger.warning("TASK: Log uploading disabled. Unscheduling task")
        upload_logs.stop()
    elif not s3.upload_logs():
        Logger.error("TASK: Unable to upload logs. Unscheduling task")
        upload_logs.stop()
    else:
        Logger.info("TASK: Logs uploaded")


# Misc and helpers


async def __set_presence():
    """Set the bot's presence message."""
    servers = len(bot.guilds)
    message = f"/help | {servers} chronicles"

    Logger.info("BOT: Setting presence")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=message)
    )


def setup():
    """Add the cogs to the bot."""
    for filename in os.listdir("./interface"):
        if filename[0] != "_" and filename.endswith(".py"):
            Logger.debug("COGS: Loading %s", filename)
            bot.load_extension(f"interface.{filename[:-3]}")

    if (topgg_token := os.getenv("TOPGG_TOKEN")) is not None:
        Logger.info("BOT: Establishing top.gg connection")
        bot.dblpy = topgg.DBLClient(bot, topgg_token, autopost=True)
    else:
        Logger.warning("BOT: top.gg not configured")


async def run():
    """Set up and run the bot."""
    setup()
    try:
        await bot.start(os.environ["INCONNU_TOKEN"])
    except KeyboardInterrupt:
        Logger.info("BOT: Logging out")
        await bot.bot.logout()
