"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI, SelectedMenu

import inconnu
import c_help

bot = commands.Bot(command_prefix="//", case_insensitive=True)
_ = UI(bot)


# Gameplay Commands

class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    @commands.command(
        name="v", aliases=["roll", "r"],
        brief=c_help.ROLL_BRIEF,
        description=c_help.ROLL_DESC,
        usage=c_help.ROLL_USAGE,
        help=c_help.ROLL_HELP
    )
    async def roll(self, ctx, *, args=None):
        """Roll a dice pool, either raw or calculated from traits."""
        if args is not None:
            await inconnu.roll.parse(ctx, args)

    @commands.command(
        brief = c_help.ROUSE_BRIEF,
        usage=c_help.ROUSE_USAGE,
        help=c_help.ROUSE_HELP
    )
    async def rouse(self, ctx, *args):
        """Perform a rouse check."""
        await inconnu.rousemorse.parse(ctx, "rouse", *args)


    @commands.command(
        brief = c_help.REMORSE_BRIEF,
        usage=c_help.REMORSE_USAGE,
        help=c_help.REMORSE_HELP
    )
    async def remorse(self, ctx, *args):
        """Perform a remorse check."""
        await inconnu.rousemorse.parse(ctx, "remorse", *args)


    @commands.command(
        brief = c_help.RESONANCE_BRIEF,
        help=c_help.RESONANCE_HELP
    )
    async def resonance(self, ctx):
        """Perform a resonance check."""
        await inconnu.resonance.generate(ctx)


# Character CRUD

class CharacterCommands(commands.Cog, name="Character Management"):
    """Character management commands."""

    @commands.command(
        name="new", aliases=["n"],
        brief = c_help.CHAR_NEW_BRIEF,
        description = c_help.CHAR_NEW_DESCRIPTION,
        usage = c_help.CHAR_NEW_USAGE,
        help = c_help.CHAR_NEW_HELP
    )
    @commands.guild_only()
    async def new_character(self, ctx, *args):
        """Create a new character."""
        await inconnu.newchar.parse(ctx, *args)


    @commands.command(
        name="display", aliases=["d", "find", "f", "list", "l"],
        brief = c_help.CHAR_DISPLAY_BRIEF,
        usage = c_help.CHAR_DISPLAY_USAGE,
        help = c_help.CHAR_DISPLAY_HELP
    )
    @commands.guild_only()
    async def display_character(self, ctx, *args):
        """Display a character's basic traits"""
        await inconnu.display.parse(ctx, *args)


    @commands.command(
        name="update", aliases=["u", "up"],
        brief = c_help.CHAR_UPDATE_BRIEF,
        usage = c_help.CHAR_UPDATE_USAGE,
        help = c_help.CHAR_UPDATE_HELP
    )
    @commands.guild_only()
    async def update_character(self, ctx, *args):
        """Update a character's parameters but not the traits."""
        await inconnu.update.parse(ctx, *args)


    @commands.command(
        name="delete", aliases=["del"],
        brief = c_help.CHAR_DELETE_BRIEF,
        usage = c_help.CHAR_DELETE_USAGE,
        help = c_help.CHAR_DELETE_HELP
    )
    @commands.guild_only()
    async def delete_character(self, ctx, char_name):
        """Delete a character."""
        await inconnu.delete.prompt(ctx, char_name)


# Trait CRUD

class TraitCommands(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.group(
        invoke_without_command=True, name="traits", aliases=["trait", "t"],
        brief = c_help.TRAITS_COMMAND_BRIEF,
        usage = c_help.TRAITS_COMMAND_USAGE,
        help = c_help.TRAITS_COMMAND_HELP
    )
    async def modify_traits(self, ctx):
        """Traits subcommand start."""
        await ctx.reply("Uh, you need to do more, dude")


    @modify_traits.command(
        name="add",
        brief = c_help.TRAITS_ADD_BRIEF,
        usage = c_help.TRAITS_ADD_USAGE,
        help = c_help.TRAITS_ADD_HELP
    )
    async def add_trait(self, ctx, *args):
        """Add trait(s) to a character."""
        await inconnu.traits.add_update.parse(ctx, False, *args)


    @modify_traits.command(
        name="list", aliases=["show", "s"],
        brief = c_help.TRAITS_LIST_BRIEF,
        usage = c_help.TRAITS_LIST_USAGE,
        help = c_help.TRAITS_LIST_HELP
    )
    async def list_traits(self, ctx, *args):
        """Display a character's traits."""
        await inconnu.traits.show.parse(ctx, *args)


    @modify_traits.command(
        name="update",
        brief = c_help.TRAITS_UPDATE_BRIEF,
        usage = c_help.TRAITS_UPDATE_USAGE,
        help = c_help.TRAITS_UPDATE_HELP
    )
    async def update_traits(self, ctx, *args):
        """Update a character's trait(s)."""
        await inconnu.traits.add_update.parse(ctx, True, *args)


    @modify_traits.command(
        name="delete", aliases=["rm"],
        brief = c_help.TRAITS_DELETE_BRIEF,
        usage = c_help.TRAITS_DELETE_USAGE,
        help = c_help.TRAITS_DELETE_HELP
    )
    async def delete_traits(self, ctx, *args):
        """Remove traits from a character."""
        await inconnu.traits.delete.parse(ctx, *args)


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


def setup():
    """Final bot setup."""
    bot.add_cog(Gameplay(bot))
    bot.add_cog(CharacterCommands(bot))
    bot.add_cog(TraitCommands(bot))
