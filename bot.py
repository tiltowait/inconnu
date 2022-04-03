"""commands.py - Define the commands and event handlers for the bot."""

import asyncio
import os

import discord
import pymongo.errors
import topgg
from discord.ext import commands, tasks

import inconnu

# Check if we're in dev mode
if (debug_guild := os.getenv("DEBUG")) is not None:
    print("Debugging on", debug_guild)
    debug_guild = [int(debug_guild)]


# Set up the bot instance
intents = discord.Intents(guilds=True, members=True)
bot = discord.Bot(intents=intents, debug_guilds=debug_guild)
bot.persistent_views_added = False
bot.welcomed = False


# General Events


@bot.event
async def on_ready():
    """Schedule a task to perform final setup."""
    task = bot.loop.create_task(finish_setup())
    await task


async def finish_setup():
    """Print login message and perform final setup."""
    if bot.welcomed:
        return

    await bot.wait_until_ready()

    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)
    print("Latency:", bot.latency * 1000, "ms")
    print("------------")

    await __set_presence()
    cull_inactive.start()
    inconnu.char_mgr.bot = bot
    bot.welcomed = True


@bot.event
async def on_application_command_error(ctx, error):
    """Handle various errors we might encounter."""
    error = getattr(error, "original", error)  # Some pycord errors have `original`, but not all

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.respond("Sorry, this command can only be run in a server!", ephemeral=True)
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("Sorry, you don't have permission to do this!", ephemeral=True)
        return
    if isinstance(error, discord.errors.NotFound):
        # This just means a button tried to disable when its message no longer exists.
        # We don't care, and there's nothing we can do about it anyway.
        return

    # Unknown errors and database errors are logged to a channel

    if isinstance(error, pymongo.errors.PyMongoError):
        await inconnu.log.report_database_error(bot, ctx)
        return

    await inconnu.log.report_error(bot, ctx, error)


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
    print(f"Joined {guild.name}!")
    await asyncio.gather(inconnu.stats.guild_joined(guild), __set_presence())


@bot.event
async def on_guild_remove(guild):
    """Log guild removals."""
    print(f"Left {guild.name} :(")
    await asyncio.gather(inconnu.stats.guild_left(guild.id), __set_presence())


@bot.event
async def on_guild_update(before, after):
    """Log guild name changes."""
    if before.name != after.name:
        print(f"Renamed {before.name} => {after.name}")
        await inconnu.stats.guild_renamed(after.id, after.name)


# Tasks


@tasks.loop(hours=24)
async def cull_inactive():
    """Cull inactive characters and guilds."""
    await inconnu.culler.cull()


# Misc and helpers


async def __set_presence():
    """Set the bot's presence message."""
    servers = len(bot.guilds)
    message = f"/help | {servers} chronicles"

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=message)
    )


def setup():
    """Add the cogs to the bot."""
    for filename in os.listdir("./interface"):
        if filename[0] != "_" and filename.endswith(".py"):
            bot.load_extension(f"interface.{filename[:-3]}")

    if (topgg_token := os.getenv("TOPGG_TOKEN")) is not None:
        print("Establishing top.gg connection.")
        bot.dblpy = topgg.DBLClient(bot, topgg_token, autopost=True)
