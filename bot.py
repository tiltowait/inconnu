"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI

import interface

bot = commands.Bot(command_prefix="//", case_insensitive=True)
_ = UI(bot, slash_options={"delete_unused": True})

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


# Misc and helpers

def __status_message():
    """Sets the bot's Discord presence message."""
    servers = len(bot.guilds)
    return f"//help | {servers} chronicles"


def setup():
    """Add the cogs to the bot."""
    bot.add_cog(interface.Gameplay(bot))
    bot.add_cog(interface.Macros(bot))
    bot.add_cog(interface.Characters(bot))
    bot.add_cog(interface.Traits(bot))
