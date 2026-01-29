"""common.py - Commonly used functions."""

import re
from typing import Any

import discord
from discord.ui import Button
from loguru import logger

import inconnu
import ui


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes", "die": "dice", "specialty": "specialties"}

    pluralized = f"{value} {noun}"
    if value != 1:
        if (plural := nouns.get(noun.lower())) is not None:
            if noun[0].isupper():
                plural = plural.capitalize()
            pluralized = f"{value} {plural}"
        else:
            pluralized += "s"

    return pluralized


async def present_error(
    ctx,
    error,
    *fields,
    author=None,
    character: str | None = None,
    footer: str | None = None,
    help_url: str | None = None,
    view=None,
    ephemeral=True,
):
    """
    Display an error in a nice embed.
    Args:
        ctx: The Discord context for sending the response.
        error: The error message to display.
        fields (list): Fields to add to the embed. (fields.0 is name; fields.1 is value)
        author (discord.Member): The member the message is attributed to, if not the same as ctx
        character (str): The character the message is attributed to
        footer (str): Footer text to display.
        help_url (str): The documentation URL for the error.
        components (list): Buttons or selection menus to add to the message.
    """
    msg_contents: dict[str, Any] = {}

    if await inconnu.settings.accessible(ctx):
        content = __error_text(error, *fields, footer=footer)
        msg_contents = {"content": content}
    else:
        embed = __error_embed(
            ctx,
            error,
            *fields,
            author=author,
            character=character,
            footer=footer,
        )
        msg_contents = {"embed": embed}

    # Finish preparing the response
    msg_contents["ephemeral"] = ephemeral
    msg_contents["allowed_mentions"] = discord.AllowedMentions.none()

    if help_url is not None:
        # If we have a help URL, we will add some links to the view
        view = view or ui.views.ReportingView()

        view.add_item(Button(label="Documentation", url=help_url, row=1))
        view.add_item(Button(label="Support", url=inconnu.constants.SUPPORT_URL, row=1))

    if view is not None:
        msg_contents["view"] = view

    msg = await ctx.respond(**msg_contents)

    if isinstance(view, ui.views.DisablingView):
        # So it can automatically disable its buttons
        view.message = msg

    return msg


def __error_embed(
    ctx,
    error,
    *fields,
    author=None,
    character: str | None = None,
    footer: str | None = None,
):
    # Figure out the author
    if author is None:
        avatar = inconnu.get_avatar(ctx.user)
        display_name = ctx.user.display_name
    else:
        avatar = inconnu.get_avatar(author)
        display_name = author.display_name

    if character is not None:
        if isinstance(character, str):
            display_name = character
        else:
            display_name = character.name

    embed = discord.Embed(title="Error", description=str(error), color=0xFF0000)
    embed.set_author(name=display_name, icon_url=avatar)

    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=False)

    if footer is not None:
        embed.set_footer(text=footer)

    return embed


def __error_text(
    error,
    *fields,
    footer: str | None = None,
):
    """Display the error as plaintext."""
    contents = ["**Error**", str(error) + "\n"]

    for field in fields:
        contents.append(f"{field[0]}: {field[1]}")

    if footer is not None:
        contents.append(f"```{footer}```")

    return "\n".join(contents)


async def report_update(*, ctx, character, title, message, **kwargs):
    """Display character updates in the update channel."""
    if update_channel := await inconnu.settings.update_channel(ctx.guild):
        msg = kwargs.pop("msg", None)
        if msg:
            msg = msg.jump_url

        if "embed" not in kwargs:
            embed = discord.Embed(
                title=title,
                description=message,
                url=msg,
                color=kwargs.pop("color", None),
            )
            embed.set_author(name=character.name, icon_url=inconnu.get_avatar(ctx.user))
            content = ""
        else:
            embed = kwargs["embed"]
            content = message

        mentions = discord.AllowedMentions(users=False)

        try:
            await update_channel.send(content, embed=embed, allowed_mentions=mentions)
        except discord.errors.Forbidden:
            logger.warning(
                "UPDATE REPORT: No access to post in #{} on {}",
                update_channel.name,
                update_channel.guild.name,
            )


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


def paginate(page_size: int, *contents) -> list:
    """Break the contents into pages to fit a Discord message."""
    contents = list(contents)
    pages = []

    if isinstance(contents[0], str):
        page = contents.pop(0)
        for item in contents:
            if len(page) >= page_size:
                pages.append(page)
                page = item
            else:
                page += "\n" + item

    else:
        # [[(header, contents), (header, contents), (header, contents)]]
        page = [contents.pop(0)]
        page_len = len(page[0].name) + len(page[0].value)
        for item in contents:
            if page_len >= page_size:
                pages.append(page)
                page = [item]
                page_len = len(item.name) + len(item.value)
            else:
                page_len += len(item.name) + len(item.value)
                page.append(item)

    pages.append(page)
    return pages


def contains_digit(string: str | None):
    """Determine whether a string contains a digit."""
    if string is None:
        return False
    return bool(re.search(r"\d", string))  # Much faster than using any()
