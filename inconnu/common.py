"""common.py - Commonly used functions."""

from types import SimpleNamespace

import discord
from discord_ui import Button, SelectMenu, SelectOption

from .vchar import VChar


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes"}

    pluralized = f"{value} {noun}"
    if value != 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized


async def display_error(ctx, char_name, error, *fields, footer=None, components=None):
    """Display an error in a nice embed."""
    embed = discord.Embed(
        title="Error",
        description=str(error),
        color=0xFF0000
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    for field in fields:
        embed.add_field(name=field[0], value=field[1])

    if footer is not None:
        embed.set_footer(text=footer)

    return await ctx.respond(embed=embed, components=components, hidden=True)


def command_tip(command: str, raw_syntax: str, *args):
    """Generate a string that displays a suggested fix for the command syntax."""
    return f"`{command}` `{raw_syntax}` `{' '.join(args)}`"


def character_options(guild: int, user: int):
    """
    Generate a dictionary of characters keyed by ID plus components for selecting them.
    Under 6 characters: Buttons
    Six or more characters: Selections
    """
    characters = VChar.all_characters(guild, user)
    chardict = {str(char.id): char for char in characters}

    if len(characters) < 6:
        components = [Button(str(char.id), char.name) for char in characters]
    else:
        options = [SelectOption(str(char.id), char.name) for char in characters]
        menu = SelectMenu("character_selector", options=options, placeholder="Select a character")
        components = [menu]

    return SimpleNamespace(characters=chardict, components=components)
