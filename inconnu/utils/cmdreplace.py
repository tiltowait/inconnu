"""A tool for substituting `/command` text into command mentions."""

import re

from discord import ApplicationContext

from logger import Logger


async def cmd_replace(ctx: ApplicationContext, content: str = None, **kwargs):
    """Substitute command names for command mentions and respond."""
    if isinstance(ctx, ApplicationContext):
        bot = ctx.bot
    else:
        bot = ctx.client

    # Inlines so the bot doesn't have to be passed all over the place
    def _get_command_strings(text: str) -> list[str]:
        """Returns all unique command strings in the text."""
        return list(set(re.findall(r"`/[A-Za-z]+[A-Za-z_\s]*`", text)))

    def _get_command_mention(cmd_str: str) -> str:
        """Gets the command mention from a command string."""
        cmd_name = cmd_str[2:-1]
        return bot.cmd_mention(cmd_name)

    def _sub(text: str):
        """Perform the substitution on the text."""
        if text:
            command_strings = _get_command_strings(text)
            for cmd_str in command_strings:
                mention = _get_command_mention(cmd_str)
                text = text.replace(cmd_str, mention)

                Logger.debug("CMD REPLACER: Replaced %s with %s", cmd_str, mention)

        return text

    # Perform the substitutions
    content = _sub(content)

    if (embed := kwargs.get("embed")) is not None:
        embed.description = _sub(embed.description)

        for field in embed.fields:
            field.value = _sub(field.value)

    # Send the response
    return await ctx.respond(content, **kwargs)
