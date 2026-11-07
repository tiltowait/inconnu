"""Permission and supporter status checks."""

import discord
from loguru import logger

from config import settings
from ctx import AppCtx, AppInvocation
from models import VGuild


async def is_approved_user(ctx: AppInvocation, owner: discord.User | None = None) -> bool:
    """Check if the user owns the object or is a Storyteller."""
    if ctx.user is None:
        raise ValueError("Unexpectedly got null user")

    if owner == ctx.user.id:
        return True
    return await is_storyteller(ctx.user)


def is_admin(user: discord.Member | discord.User | None) -> bool:
    """Whether the user is an administrator of the server they're acting in.

    Administrator is server-wide (channel overwrites can't remove it), so the
    member's server permissions decide it. Users outside a server never are."""
    return isinstance(user, discord.Member) and user.guild_permissions.administrator


async def is_storyteller(member: discord.Member | discord.User | None) -> bool:
    """Check if the guild member is an admin or has that server's Storyteller role.
    Users outside a server never are."""
    if not isinstance(member, discord.Member):
        return False
    if is_admin(member):
        return True

    vguild = await VGuild.get_or_fetch(member.guild)
    if vguild.settings.storyteller_role is not None:
        return member.get_role(vguild.settings.storyteller_role) is not None
    return False


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
    try:
        guild = await ctx.bot.fetch_guild(settings.supporter_guild)
        member = await guild.fetch_member(user.id)
    except discord.NotFound:
        return False

    return has_supporter_role(member)


def is_supporter(ctx: AppInvocation, user: discord.Member | discord.User | None = None) -> bool:
    """Returns True if the user invoking the command is a supporter.

    Requires settings.supporter_guild and settings.supporter_role to be set."""
    support_server = ctx.client.get_guild(settings.supporter_guild)
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
