"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands

import inconnu

bot = commands.Bot(command_prefix="//", case_insensitive=True)

@bot.command(name="v", aliases=["roll", "r"])
async def roll(ctx, *args):
    """Roll a dice pool, either raw or calculated from traits."""
    if len(args) > 0:
        await inconnu.roll.parse(ctx, *args)


# Character CRUD

@bot.command(name="new", aliases=["n"])
async def new_character(ctx, *args):
    """Create a new character."""
    await inconnu.newchar.parse(ctx, *args)


# Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)

    await bot.change_presence(activity=discord.Game(__status_message()))

@bot.event
async def on_message(message):
    """Process messages based on if they're in a guild or a private message."""
    if message.author == bot.user:
        return

    if not message.guild:
        await inconnu.newchar.process_response(message)
    else:
        await bot.process_commands(message)


# Misc and helpers

def __status_message():
    """Sets the bot's Discord presence message."""
    servers = len(bot.guilds)
    return f"!m help | {servers} chronicles"
