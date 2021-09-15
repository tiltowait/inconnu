"""common.py - Commonly used functions."""

import asyncio
from types import SimpleNamespace

import discord
from discord_ui import Button, SelectMenu, SelectOption
from discord_ui.components import LinkButton

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


async def display_error(ctx, char_name, error, help_url, *fields, footer=None, components=None):
    """
    Display an error in a nice embed.
    Args:
        ctx: The Discord context for sending the response.
        char_name (str): The name to display in the author field.
        error: The error message to display.
        help_url (str): The documentation URL for the error.
        fields (list): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        footer (str): Footer text to display.
        components (list): Buttons or selection menus to add to the message.
    """
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

    link = [LinkButton(
        help_url,
        label="Help"
    )]

    if components is None:
        components = link
    else:
        components = [components, link]

    return await ctx.respond(embed=embed, components=components, hidden=True)


async def select_character(ctx, err, help_url, tip):
    """A prompt for the user to select a character from a list."""
    options = character_options(ctx.guild.id, ctx.author.id)
    errmsg = await display_error(
        ctx, ctx.author.display_name, err, help_url, (tip[0], tip[1]),
        components=options.components
    )

    try:
        if isinstance(options.components[0], Button):
            btn = await errmsg.wait_for("button", ctx.bot, timeout=60)
            character = options.characters[btn.custom_id]
        else:
            btn = await errmsg.wait_for("select", ctx.bot, timeout=60)
            character = options.characters[btn.selected_values[0]]

        await btn.respond()
        await errmsg.disable_components()

        return character

    except asyncio.exceptions.TimeoutError:
        await errmsg.edit(components=None)
        return None


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
