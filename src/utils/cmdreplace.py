"""A tool for substituting `/command` text into command mentions."""

import re
from typing import Any

import discord
from loguru import logger

from ctx import AppInvocation


async def cmd_replace(ctx: AppInvocation, content: str | None = None, **kwargs: Any):
    """Substitute command names for command mentions and respond."""

    # Inlines so the bot doesn't have to be passed all over the place
    def _get_command_strings(text: str) -> list[str]:
        """Returns all unique command strings in the text."""
        return list(set(re.findall(r"`/[A-Za-z]+[A-Za-z_\s]*`", text)))

    def _get_command_mention(cmd_str: str) -> str | None:
        """Gets the command mention from a command string."""
        cmd_name = cmd_str[2:-1]
        return ctx.bot.cmd_mention(cmd_name)

    def _sub(text: str | None):
        """Perform the substitution on the text."""
        if text:
            command_strings = _get_command_strings(text)
            for cmd_str in command_strings:
                if mention := _get_command_mention(cmd_str):
                    text = text.replace(cmd_str, mention)
                    logger.debug("CMD REPLACER: Replaced {} with {}", cmd_str, mention)

        return text

    # Perform the substitutions
    content = _sub(content)

    if (embed := kwargs.get("embed")) is not None:
        embed.description = _sub(embed.description)

        for field in embed.fields:
            field.value = _sub(field.value)

    try:
        return await ctx.respond(content, **kwargs)
    except discord.errors.InteractionResponded:
        return None
