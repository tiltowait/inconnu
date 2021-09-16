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


async def select_character(ctx, err, help_url, tip, player=None):
    """
    A prompt for the user to select a character from a list.
    Args:
        ctx: Discord context
        err: An error message to display
        help_url: A URL pointing to the documentation
        tip (tuple): A name and value for an embed field
        player: (Optional) A Discord member to query instead
    """
    user = ctx.author if player is None else player
    options = character_options(ctx.guild.id, user.id)
    errmsg = await display_error(
        ctx, user.display_name, err, help_url, (tip[0], tip[1]),
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


async def player_lookup(ctx, player_str: str):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player_str is None.

    Raises PermissionError if the user doesn't have admin permissions.
    Raises ValueError if player is not a valid player name.
    """
    if player_str is None:
        return ctx.author

    player = player_str.strip(' <@!>')
    if not player.isdigit():
        raise LookupError(f"`{player_str}` is not a valid player.")

    player_id = int(player)
    player = await ctx.bot.fetch_user(player_id)

    if player is None:
        raise LookupError(f"`{player_str}` is not a valid player.")

    # Players are allowed to look up themselves
    if not ctx.author.guild_permissions.administrator and ctx.author != player:
        raise LookupError("You don't have lookup permissions.")

    return player
