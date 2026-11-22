"""Permission checks."""

import discord

from ctx import AppInvocation
from models import VGuild


async def is_approved_user(ctx: AppInvocation, owner: int | None = None) -> bool:
    """Check if the user owns the object (owner is a user ID) or is a Storyteller."""
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
