"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI
from discord_ui.components import LinkButton

import inconnu
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
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

    embed.add_field(name="Roll", value="`/vr pool hunger difficulty`", inline=False)
    char_info = "`/character create`\nIf you have a character, you can use their traits in rolls."
    embed.add_field(name="Create a character", value=char_info, inline=False)
    embed.add_field(name="Display character", value="`/character display`", inline=False)
    embed.add_field(name="Add traits", value="`/traits add`")

    button = LinkButton(
        "https://www.inconnu-bot.com/#/quickstart",
        label="New? Read the Quickstart!"
    )

    await ctx.respond(embed=embed, components=[button])


# Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)
    print("Latency:", bot.latency * 1000, "ms")

    await __set_presence()


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
    print(f"Renamed {before.name} => {after.name}")
    inconnu.stats.Stats.guild_renamed(after.id, after.name)


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
    bot.add_cog(interface.Gameplay(bot))
    bot.add_cog(interface.Macros(bot))
    bot.add_cog(interface.Characters(bot))
    bot.add_cog(interface.Traits(bot))
