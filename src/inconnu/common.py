"""common.py - Commonly used functions."""

import discord
from loguru import logger

import inconnu


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
