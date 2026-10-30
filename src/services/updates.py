"""Posts to the guild's update channel."""

import discord
from loguru import logger

from ctx import AppInvocation
from models import VChar
from services import settings
from utils import get_avatar


async def post_update(
    *,
    ctx: AppInvocation,
    character: VChar | None,
    title: str,
    message: str,
    msg: discord.Message | None = None,
    color: discord.Color | int | None = None,
    embed: discord.Embed | None = None,
) -> discord.Message | None:
    """Post updates in the guild's update channel. Returns the sent
    message, if any.

    Without an embed, one is built from the title, message, character, color,
    and a link to msg. With an embed, the message is sent alongside it, and the
    rest is unused."""
    if ctx.guild is None:
        # Update channels only exist in guilds
        return None

    # The settings menu only offers text channels
    update_channel = await settings.update_channel(ctx.guild)
    if isinstance(update_channel, discord.TextChannel):
        if embed is None:
            # Only updates with their own embed may omit the character
            assert character is not None
            embed = discord.Embed(
                title=title,
                description=message,
                url=msg.jump_url if msg else None,
                color=color,
            )
            embed.set_author(name=character.name, icon_url=get_avatar(ctx.user))
            content = ""
        else:
            content = message

        mentions = discord.AllowedMentions(users=False)

        try:
            return await update_channel.send(content, embed=embed, allowed_mentions=mentions)
        except discord.errors.Forbidden:
            logger.warning(
                "No access to post in #{} on {}",
                update_channel.name,
                update_channel.guild.name,
            )
