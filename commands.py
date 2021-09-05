"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI, SelectedMenu

import inconnu

bot = commands.Bot(command_prefix="//", case_insensitive=True)
_ = UI(bot)


# Gameplay Commands

@bot.command(name="v", aliases=["roll", "r"])
async def roll(ctx, *, args=None):
    """Roll a dice pool, either raw or calculated from traits."""
    if args is not None:
        await inconnu.roll.parse(ctx, args)

@bot.command()
async def rouse(ctx, *args):
    """Perform a rouse check."""
    await inconnu.rousemorse.parse(ctx, "rouse", *args)


@bot.command()
async def remorse(ctx, *args):
    """Perform a remorse check."""
    await inconnu.rousemorse.parse(ctx, "remorse", *args)


@bot.command()
async def resonance(ctx):
    """Perform a resonance check."""
    await inconnu.resonance.generate(ctx)


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


@bot.command(name="delete", aliases=["del"])
@commands.guild_only()
async def delete_character(ctx, char_name):
    """Delete a character."""
    await inconnu.delete.prompt(ctx, char_name)


# Trait CRUD

@bot.group(invoke_without_command=True, name="traits", aliases=["trait", "t"])
async def modify_traits(ctx):
    """Traits subcommand start."""
    await ctx.reply("Uh, you need to do more, dude")


@modify_traits.command(name="add")
async def add_trait(ctx, *args):
    """Add trait(s) to a character."""
    await inconnu.traits.add_update.parse(ctx, False, *args)


@modify_traits.command(name="list", aliases=["show", "s"])
async def list_traits(ctx, *args):
    """Display a character's traits."""
    await inconnu.traits.show.parse(ctx, *args)


@modify_traits.command(name="update")
async def update_traits(ctx, *args):
    """Update a character's trait(s)."""
    await inconnu.traits.add_update.parse(ctx, True, *args)


@modify_traits.command(name="delete")
async def delete_traits(ctx, *args):
    """Remove traits from a character."""
    await ctx.reply("Remove traits")


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

    raise error


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
