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
