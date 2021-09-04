"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI, SelectedMenu

import inconnu

bot = commands.Bot(command_prefix="//", case_insensitive=True)
_ = UI(bot)

@bot.command(name="v", aliases=["roll", "r"])
async def roll(ctx, *args):
    """Roll a dice pool, either raw or calculated from traits."""
    if len(args) > 0:
        await inconnu.roll.parse(ctx, *args)

@bot.command()
async def rouse(ctx, *args):
    """Perform a rouse check."""
    await inconnu.rousemorse.parse(ctx, "rouse", *args)


@bot.command()
async def remorse(ctx, *args):
    """Perform a remorse check."""
    await inconnu.rousemorse.parse(ctx, "remorse", *args)


# Character CRUD

@bot.command(name="new", aliases=["n"])
@commands.guild_only()
async def new_character(ctx, *args):
    """Create a new character."""
    await inconnu.newchar.parse(ctx, *args)


@bot.command(name="display", aliases=["d", "find", "f", "list", "l"])
@commands.guild_only()
async def display_character(ctx, *args):
    """Display a character's basic traits."""
    await inconnu.display.parse(ctx, *args)


@bot.command(name="update", aliases=["u", "up"])
@commands.guild_only()
async def update_character(ctx, *args):
    """Update a character's parameters but not the traits."""
    await inconnu.update.parse(ctx, *args)


# Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)

    await bot.change_presence(activity=discord.Game(__status_message()))


@bot.event
async def on_command_error(ctx, error):
    """Handle various errors we might encounter."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("Sorry, this command isn't available in DMs!")
        return

    print(error)


@bot.listen("on_menu_select")
async def on_button(menu: SelectedMenu):
    """Pass the selection to the appropriate manager."""
    if menu.custom_id == "rating_selector":
        await inconnu.newchar.response_selected(menu)


# Misc and helpers

def __status_message():
    """Sets the bot's Discord presence message."""
    servers = len(bot.guilds)
    return f"!m help | {servers} chronicles"
