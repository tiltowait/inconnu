"""commands.py - Define the commands and event handlers for the bot."""

import os

import discord
import topgg
from discord.ext import commands, tasks

import inconnu

intents = discord.Intents.default()
intents.members = True # pylint: disable=assigning-non-slot

# Check if we're in dev mode
if (debug_guild := os.getenv("DEBUG")) is not None:
    print("Debugging on", debug_guild)
    debug_guild = [int(debug_guild)]

bot = discord.Bot(intents=intents, debug_guilds=debug_guild)
setattr(bot, "persistent_views_added", False)


# General Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)
    print("Latency:", bot.latency * 1000, "ms")
    print("------------")

    await __set_presence()
    cull_inactive.start()


@bot.event
async def on_application_command_error(ctx, error):
    """Handle various errors we might encounter."""
    if isinstance(error.original, commands.NoPrivateMessage):
        await ctx.respond("Sorry, this command isn't available in DMs!", ephemeral=True)
        return
    if isinstance(error.original, discord.errors.NotFound):
        # This just means a button tried to disable when its message no longer exists.
        # We don't care, and there's nothing we can do about it anyway.
        pass

    raise error


# Member Events

@bot.event
async def on_member_remove(member):
    """Mark all of a member's characters as inactive."""
    inconnu.VChar.mark_player_inactive(member)


@bot.event
async def on_member_join(member):
    """Mark all the player's characters as active when they rejoin a guild."""
    inconnu.VChar.reactivate_player_characters(member)


# Guild Events

@bot.event
async def on_guild_join(guild):
    """Log whenever a guild is joined."""
    print(f"Joined {guild.name}!")
    inconnu.stats.Stats.guild_joined(guild.id, guild.name)
    await __set_presence()


@bot.event
async def on_guild_remove(guild):
    """Log guild removals."""
    print(f"Left {guild.name} :(")
    inconnu.stats.Stats.guild_left(guild.id)
    await __set_presence()


@bot.event
async def on_guild_update(before, after):
    """Log guild name changes."""
    if before.name != after.name:
        print(f"Renamed {before.name} => {after.name}")
        inconnu.stats.Stats.guild_renamed(after.id, after.name)


# Tasks

@tasks.loop(hours=24)
async def cull_inactive():
    """Cull inactive characters and guilds."""
    inconnu.culler.cull()


# Misc and helpers

async def __set_presence():
    """Set the bot's presence message."""
    servers = len(bot.guilds)
    message = f"/help | {servers} chronicles"

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=message
        )
    )


def setup():
    """Add the cogs to the bot."""
    for filename in os.listdir("./interface"):
        if filename.endswith(".py"):
            bot.load_extension(f"interface.{filename[:-3]}")

    if (topgg_token := os.getenv("TOPGG_TOKEN")) is not None:
        print("Establishing top.gg connection.")
        bot.dblpy = topgg.DBLClient(bot, topgg_token, autopost=True)
