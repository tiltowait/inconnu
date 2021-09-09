"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI
from discord_ui.components import LinkButton

import interface

bot = commands.Bot(command_prefix="//", case_insensitive=True)
bot.remove_command("help")
ui = UI(bot, slash_options={"delete_unused": True})


# Help command

@ui.slash.command("help", description="Help with basic functions.")
async def help_command(ctx):
    """Display a help message."""
    embed = discord.Embed(
        title="Inconnu Help",
        description="Basic commands listing. Click the link for detailed documentation."
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

    embed.add_field(name="Roll", value="`/v pool hunger difficulty`", inline=False)
    char_info = "`/character create`\nIf you have a character, you can use their traits in rolls."
    embed.add_field(name="Create a character", value=char_info, inline=False)
    embed.add_field(name="Display character", value="`/character display`", inline=False)
    embed.add_field(name="Add traits", value="`/traits add`")

    button = LinkButton(
        "https://www.inconnu-bot.com/#/quickstart",
        label="New? Read the Quickstart!"
    )

    await ctx.respond(embed=embed, components=[button], hidden=True)


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
