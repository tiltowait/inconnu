"""Permission and supporter status checks."""

from typing import cast

import discord
from loguru import logger

from config import SUPPORTER_GUILD, SUPPORTER_ROLE
from ctx import AppCtx

AppInteraction = AppCtx | discord.Interaction


def is_approved_user(ctx: AppInteraction, owner_id: discord.User | None = None):
    """Check if the user owns the object or is an admin."""
    if ctx.user is None:
        raise ValueError("Unexpectedly got null user")

    if owner_id == ctx.user.id:
        return True
    return is_admin(ctx)


def is_admin(ctx: AppInteraction):
    """Check if the ctx user is a server admin."""
    if ctx.channel is None:
        raise ValueError("Unexpectedly got null channel")

    user = cast(discord.Member, ctx.user)
    if isinstance(ctx.channel, discord.PartialMessageable):
        # We can't use permissions_for
        return user.top_role.permissions.administrator or user.guild_permissions.administrator
    return ctx.channel.permissions_for(user).administrator


async def get_or_fetch_supporter(
    ctx: discord.ApplicationContext, user: discord.Member | None
) -> bool:
    """Returns True if the user or invoking user is a supporter."""
    user = user or ctx.user
    assert user is not None

    guild = ctx.bot.get_guild(SUPPORTER_GUILD)
    if guild:
        member = guild.get_member(user.id)
        if member:
            return member.get_role(SUPPORTER_ROLE) is not None

    # Fallback: Use the API instead of the cache
    guild = await ctx.bot.fetch_guild(SUPPORTER_GUILD)
    member = await guild.fetch_member(user.id)
    if member:
        return member.get_role(SUPPORTER_ROLE) is not None

    return False


def is_supporter(ctx: AppInteraction, user: discord.Member | None = None) -> bool:
    """Returns True if the user invoking the command is a supporter.

    Requires SUPPORTER_GUILD and SUPPORTER_ROLE to be set."""
    if isinstance(ctx, discord.Interaction):
        bot = ctx.client
    else:
        bot = ctx.bot
    support_server = bot.get_guild(SUPPORTER_GUILD)
    if support_server is None:
        logger.warning("Support server not set!")
        return False

    user = user or ctx.user

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(user.id)) is not None:
        logger.debug("SUPPORTER: {} is on {}", user.name, support_server.name)
        if member.get_role(SUPPORTER_ROLE) is not None:
            logger.debug("SUPPORTER: {} is a supporter", user.name)
            return True
        logger.debug("SUPPORTER: {} is a not a supporter", user.name)
        return False
    logger.debug("SUPPORTER: {} is not on the support server", user.name)
    return False
