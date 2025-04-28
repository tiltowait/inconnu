"""Commonly used utilities."""

import re
from difflib import Differ
from typing import Any

import discord
from discord.ext.commands import Paginator

import inconnu
from config import SUPPORTER_GUILD, SUPPORTER_ROLE
from inconnu.utils import decorators
from inconnu.utils.cmdreplace import cmd_replace
from inconnu.utils.decorators import not_on_lockdown
from inconnu.utils.error import ErrorEmbed, error
from inconnu.utils.haven import Haven
from inconnu.utils.paramparse import parse_parameters
from logger import Logger

__all__ = (
    "decorators",
    "cmd_replace",
    "not_on_lockdown",
    "ErrorEmbed",
    "error",
    "Haven",
    "parse_parameters",
)


def clean_text(text: str) -> str:
    """Remove extra spaces in text."""
    return " ".join(text.split())


def de_camel(text: str, de_underscore=True) -> str:
    """CamelCase -> Camel Case. Also does underscores."""
    temp = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    if de_underscore:
        return temp.replace("_", " ")
    return temp


def diff(old: str, new: str, join=True, no_pos_markers=True, strip=False) -> str:
    """Generate a diff between two strings."""

    def normalize(lines: str) -> str:
        """Normalize the lines to make more concise diffs."""
        if len(lines) == 1 and lines[0][-1] != "\n":
            lines[0] += "\n"
        return lines

    old = normalize(old.splitlines(True))
    new = normalize(new.splitlines(True))

    diff = Differ().compare(old, new)
    lines = [line + ("\n" if line[-1] != "\n" else "") for line in diff]

    if no_pos_markers:
        lines = [line for line in lines if line[0] != "?"]
    if strip:
        lines = [line.strip() for line in lines]
    if join:
        return "".join(lines)
    return lines


def raw_command_options(interaction) -> str:
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


def is_admin(ctx, owner_id=None):
    """
    Check if the ctx user is an admin.
    If owner is set, checks if it and ctx.user are equal.
    """
    if owner_id == ctx.user.id:
        return True
    if isinstance(ctx.channel, discord.PartialMessageable):
        # We can't use permissions_for
        user = ctx.user
        return user.top_role.permissions.administrator or user.guild_permissions.administrator
    return ctx.channel.permissions_for(ctx.user).administrator


def is_supporter(ctx, user: discord.Member = None) -> bool:
    """Returns True if the user invoking the command is a supporter."""
    support_server = inconnu.bot.get_guild(SUPPORTER_GUILD)
    user = user or ctx.user

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(user.id)) is not None:
        Logger.debug("SUPPORTER: %s is on %s", user.name, support_server.name)
        if member.get_role(SUPPORTER_ROLE) is not None:
            Logger.debug("SUPPORTER: %s is a supporter", user.name)
            return True
        Logger.debug("SUPPORTER: %s is a not a supporter", user.name)
        return False
    Logger.debug("SUPPORTER: %s is not on the support server", user.name)
    return False


def format_join(collection: list, separator: str, f: str, alt="") -> str:
    """Join a collection by a separator, formatting each item."""
    return separator.join(map(lambda c: f"{f}{c}{f}", collection)) or alt


def pull_mentions(text: str) -> set[str]:
    """Pulls mentions from text."""
    mentions = re.findall(r"(<(?:@|@&|#)\d{1,30}>)", text)
    return set(mentions)


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


def oxford_list(seq: list[Any], conjunction="and") -> str:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    seq = [str(s) for s in seq]
    if len(seq) < 3:
        return f" {conjunction} ".join(seq)
    return ", ".join(seq[:-1]) + f", {conjunction} " + seq[-1]


class VCharEmbed(discord.Embed):
    """A standardized VChar display."""

    def __init__(self, ctx, character, owner: discord.Member = None, link=False, **kwargs):
        owner = owner or ctx.user
        show_thumbnail = kwargs.pop("show_thumbnail", True)

        if link:
            kwargs["url"] = inconnu.profile_url(character.pk)

        if "title" in kwargs:
            author_name = character.name
        else:
            author_name = owner.name
            kwargs["title"] = character.name

        if is_supporter(ctx, owner):
            # Premium color
            kwargs["color"] = 0x00A4FF

        super().__init__(**kwargs)

        self.set_author(name=author_name, icon_url=inconnu.get_avatar(owner))

        if show_thumbnail:
            self.set_thumbnail(url=character.profile_image_url)
