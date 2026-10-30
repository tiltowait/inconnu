"""A tool for substituting `/command` text into command mentions."""

import re
from typing import TYPE_CHECKING, Any

import discord
from loguru import logger

from ctx import AppInvocation

if TYPE_CHECKING:
    from bot import InconnuBot


def mention_commands(bot: InconnuBot, text: str | None) -> str | None:
    """Substitute `/command` strings in the text for command mentions."""
    if text:
        for cmd_str in set(re.findall(r"`/[A-Za-z]+[A-Za-z_\s]*`", text)):
            if mention := bot.cmd_mention(cmd_str[2:-1]):
                text = text.replace(cmd_str, mention)
                logger.debug("Replaced {} with {}", cmd_str, mention)

    return text


def mention_embed_commands(bot: InconnuBot, embed: discord.Embed):
    """Substitute `/command` strings in the embed's description and field values."""
    embed.description = mention_commands(bot, embed.description)
    for field in embed.fields:
        field.value = mention_commands(bot, field.value) or ""


async def cmd_replace_respond(ctx: AppInvocation, content: str | None = None, **kwargs: Any):
    """Substitute command names for command mentions and respond."""
    content = mention_commands(ctx.bot, content)

    if (embed := kwargs.get("embed")) is not None:
        mention_embed_commands(ctx.bot, embed)

    return await ctx.respond(content, **kwargs)
