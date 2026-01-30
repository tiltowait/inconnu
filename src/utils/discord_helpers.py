"""Discord command and interaction helpers."""

from typing import Any

import discord
from discord.ext.commands import Paginator


def raw_command_options(interaction) -> dict[str, Any]:
    """Get the options in a command as a dict."""
    options = {}
    for option in interaction.data.get("options", []):
        name = option["name"]
        value = option["value"]
        options[name] = value

    return options


def command_options(interaction) -> str:
    """Format the command options for easy display."""
    options = []
    for option in interaction.data.get("options", []):
        _name = option["name"]
        _value = option["value"]

        # This is hardly exhaustive, since option types can also be members
        # or channels, but the main purpose with enclosing strings in quotes
        # is to remove ambiguity that might occur with more complex string
        # patterns.
        if isinstance(_value, str):
            options.append(f'{_name}="{_value}"')
        else:
            options.append(f"{_name}={_value}")

    return ", ".join(options) if options else "None"


def re_paginate(strings: list[str], *, page_len=2000) -> list[str]:
    """Adjusts the pages into the fewest number of <=2k pages possible.
    It does so via three possible methods:
      1. Newlines
      2. Spaces
      3. Individual characters
    """
    delimiter = ""
    for i in range(1, len(strings) * 2, 2):
        # Insert a newline between each page to make sure paragraphs are
        # properly broken. It's fine if the last element ends up being a
        # newline; it will be removed later.
        strings.insert(i, delimiter)

    # Default case: paginate by newlines
    lines = sum([string.split("\n") for string in strings], [])
    paginator = Paginator(prefix="", suffix="", max_size=page_len)

    try:
        for line in lines:
            paginator.add_line(line)
        return [page.strip() for page in paginator.pages]
    except RuntimeError:
        pass

    # Newlines failed; split by words
    words = sum([string.split(" ") for string in strings], [])
    paginator = Paginator(prefix="", suffix="", linesep=" ", max_size=page_len)

    try:
        for word in words:
            paginator.add_line(word)
        return [page.strip() for page in paginator.pages]
    except RuntimeError:
        pass

    # Spaces failed; split by characters
    combined = "".join(strings)
    return [combined[i : i + page_len].strip() for i in range(0, len(combined), page_len)]


async def get_message(inter):
    """Get the message from an interaction."""
    if isinstance(inter, discord.Message):
        return inter
    return await inter.original_response()


def get_avatar(user: discord.User | discord.Member):
    """Get the user's avatar."""
    if isinstance(user, discord.User):
        # Users don't have a guild presence
        return user.display_avatar

    # Members can have a guild-specific avatar
    return user.guild_avatar or user.display_avatar


async def player_lookup(ctx, player: discord.Member | None):
    """
    Look up a player.
    Returns the sought-after player OR the ctx author if player_str is None.

    Raises PermissionError if the user doesn't have admin permissions.
    Raises ValueError if player is not a valid player name.
    """
    if player is None:
        return ctx.user

    # Players are allowed to look up themselves
    if (not ctx.user.guild_permissions.administrator) and ctx.user != player:
        raise LookupError("You don't have lookup permissions.")

    return player
