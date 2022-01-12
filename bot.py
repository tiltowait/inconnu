"""commands.py - Define the commands and event handlers for the bot."""

import os

import discord
import topgg
from discord.ext import commands, tasks
from discord_ui import UI

import inconnu
import interface

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="", intents=intents, case_insensitive=True)
bot.remove_command("help")
UI(bot)


# General Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)
    print("Latency:", bot.latency * 1000, "ms")
    print("------------\n")

    await __set_presence()
    cull_inactive.start()


@bot.event
async def on_command_error(ctx, error):
    """Handle various errors we might encounter."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("Sorry, this command isn't available in DMs!")
        return

    raise error


# Guild Events

@bot.event
async def on_member_remove(member):
    """Mark all of a member's characters as inactive."""
    inconnu.VChar.mark_player_inactive(member)


@bot.event
async def on_member_join(member):
    """Mark all the player's characters as active when they rejoin a guild."""
    inconnu.VChar.reactivate_player_characters(member)


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
    bot.add_cog(interface.Characters(bot))
    bot.add_cog(interface.Help(bot))
    bot.add_cog(interface.Gameplay(bot))
    bot.add_cog(interface.Macros(bot))
    bot.add_cog(interface.MiscCommands(bot))
    bot.add_cog(interface.SettingsCommands(bot))
    bot.add_cog(interface.Traits(bot))

    if "STATCORD_TOKEN" in os.environ:
        print("Establishing statcord connection.")
        bot.add_cog(interface.StatcordPost(bot, os.environ["STATCORD_TOKEN"]))

    if "TOPGG_TOKEN" in os.environ:
        print("Establishing top.gg connection.")
        bot.dblpy = topgg.DBLClient(bot, os.environ["TOPGG_TOKEN"], autopost=True)
