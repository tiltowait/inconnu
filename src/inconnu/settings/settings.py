"""Functions for getting user/guild settings from AppCtx/Interactions."""

import discord

from ctx import AppCtx
from models import ExpPerms, VGuild, VUser
from utils.permissions import is_admin

# Accessibility


async def accessible(ctx: AppCtx | discord.Interaction):
    """Determine whether we should use accessibility mode.

    Accessibility mode disables emojis. Recommended to instead use can_emoji()
    instead, as it's easier to reason about."""
    # User accessibility trumps guild accessibility
    user_settings = await VUser.get_or_fetch(ctx.user.id)
    if user_settings.settings.accessibility:
        return True

    # Check guild accessibility
    guild = await VGuild.get_or_fetch(ctx.guild)
    if guild.settings.accessibility:
        return True

    # Finally, make sure we have emoji permission
    try:
        everyone = ctx.guild.default_role
        return not ctx.channel.permissions_for(everyone).external_emojis
    except AttributeError:
        # We somehow received a PartialMessageable or something else
        return True  # Fallback


async def can_emoji(ctx: AppCtx | discord.Interaction) -> bool:
    """Wrapper for accessible() that simply inverts the logic."""
    return not await accessible(ctx)


# XP Permissions


async def can_adjust_current_xp(ctx: AppCtx) -> bool:
    """Whether the user can adjust their current XP."""
    if is_admin(ctx):
        return True

    guild = await VGuild.get_or_fetch(ctx.guild)
    return guild.settings.experience_permissions in [
        ExpPerms.UNRESTRICTED,
        ExpPerms.UNSPENT_ONLY,
    ]


async def can_adjust_lifetime_xp(ctx: AppCtx) -> bool:
    """Whether the user has permission to adjust lifetime XP."""
    if is_admin(ctx):
        return True

    guild = await VGuild.get_or_fetch(ctx.guild)
    return guild.settings.experience_permissions in [
        ExpPerms.UNRESTRICTED,
        ExpPerms.LIFETIME_ONLY,
    ]


# Oblivion stains


async def oblivion_stains(guild: discord.Guild) -> list:
    """Retrieve the Rouse results that grant Oblivion stains."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.oblivion_stains


# Update Channels


async def update_channel(guild: discord.Guild):
    """Retrieve the ID of the guild's update channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    if update_channel := vguild.settings.update_channel:
        return guild.get_channel(update_channel)

    return None


async def changelog_channel(guild: discord.Guild) -> int | None:
    """Retrieves the ID of the guild's RP changelog channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.changelog_channel


async def deletion_channel(guild: discord.Guild) -> int | None:
    """Retrieves the ID of the guild's RP deletion channel, if any."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.deletion_channel


async def add_empty_resonance(guild: discord.Guild):
    """Whether to add Empty Resonance to the Resonance table."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.add_empty_resonance


async def max_hunger(guild: discord.Guild):
    """Get the max Hunger rating allowed in rolls."""
    vguild = await VGuild.get_or_fetch(guild)
    return vguild.settings.max_hunger
