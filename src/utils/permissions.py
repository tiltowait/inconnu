"""Permission and supporter status checks."""

import discord
from loguru import logger

from config import settings
from ctx import AppCtx, AppInvocation


def is_approved_user(ctx: AppInvocation, owner: discord.User | None = None):
    """Check if the user owns the object or is an admin."""
    if ctx.user is None:
        raise ValueError("Unexpectedly got null user")

    if owner == ctx.user.id:
        return True
    return is_admin(ctx.user)


def is_admin(user: discord.Member | discord.User | None) -> bool:
    """Whether the user is an administrator of the server they're acting in.

    Administrator is server-wide (channel overwrites can't remove it), so the
    member's server permissions decide it. Users outside a server never are."""
    return isinstance(user, discord.Member) and user.guild_permissions.administrator


def has_supporter_role(member: discord.Member) -> bool:
    """Whether the member has the supporter role."""
    return member.get_role(settings.supporter_role) is not None


async def get_or_fetch_supporter(ctx: AppCtx, user: discord.Member | discord.User | None) -> bool:
    """Returns True if the user or invoking user is a supporter."""
    user = user or ctx.user
    assert user is not None

    guild = ctx.bot.get_guild(settings.supporter_guild)
    if guild:
        member = guild.get_member(user.id)
        if member:
            return has_supporter_role(member)

    # Fallback: Use the API instead of the cache
    guild = await ctx.bot.fetch_guild(settings.supporter_guild)
    member = await guild.fetch_member(user.id)
    if member:
        return has_supporter_role(member)

    return False


def is_supporter(ctx: AppInvocation, user: discord.Member | discord.User | None = None) -> bool:
    """Returns True if the user invoking the command is a supporter.

    Requires settings.supporter_guild and settings.supporter_role to be set."""
    if isinstance(ctx, discord.Interaction):
        bot = ctx.client
    else:
        bot = ctx.bot
    support_server = bot.get_guild(settings.supporter_guild)
    if support_server is None:
        logger.warning("Support server not set!")
        return False

    user = user or ctx.user
    if user is None:
        return False

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(user.id)) is not None:
        logger.debug("SUPPORTER: {} is on {}", user.name, support_server.name)
        if has_supporter_role(member):
            logger.debug("SUPPORTER: {} is a supporter", user.name)
            return True
        logger.debug("SUPPORTER: {} is a not a supporter", user.name)
        return False
    logger.debug("SUPPORTER: {} is not on the support server", user.name)
    return False
