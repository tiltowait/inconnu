"""Fresh Discord authorization for the narrow roll export."""

import asyncio
from typing import TYPE_CHECKING

import aiohttp
import discord
from pymongo.errors import PyMongoError

from errors import IntegrationError
from models import VGuild
from utils.permissions import is_storyteller_role

if TYPE_CHECKING:
    from bot import InconnuBot


ACCESS_TIMEOUT = 7


def eligible(
    member: discord.Member, channel: discord.abc.GuildChannel, storyteller_role: int | None
) -> bool:
    """Require the shared Storyteller policy and readable ordinary text channel."""
    if (
        not isinstance(member, discord.Member)
        or not isinstance(channel, discord.TextChannel)
        or channel.type != discord.ChannelType.text
        or channel.guild.id != member.guild.id
        or not is_storyteller_role(member, storyteller_role)
    ):
        return False
    permissions = channel.permissions_for(member)
    return permissions.view_channel and permissions.read_message_history


def _require_connected(bot: InconnuBot, guild_id: int) -> None:
    """Require a ready bot and a connected shard for the guild."""
    guild = bot.get_guild(guild_id)
    if not bot.is_ready() or bot.is_closed():
        raise IntegrationError(503, "Discord authorization unavailable")
    if guild is None:
        raise IntegrationError(403, "Channel access denied")
    shard = bot.get_shard(guild.shard_id)
    if guild.unavailable or shard is None or shard.is_closed():
        raise IntegrationError(503, "Discord authorization unavailable")


async def authorize_channel(bot: InconnuBot, owner_id: int, guild_id: int, channel_id: int) -> None:
    """Require a current Storyteller and access to one ordinary text channel."""
    _require_connected(bot, guild_id)
    try:
        async with asyncio.timeout(ACCESS_TIMEOUT):
            guild = await bot.fetch_guild(guild_id)
            member = await guild.fetch_member(owner_id)
            channel = await bot.fetch_channel(channel_id)
            vguild = await VGuild.find_one({"guild": guild_id})
    except (discord.NotFound, discord.Forbidden) as exc:
        raise IntegrationError(403, "Channel access denied") from exc
    except (discord.HTTPException, aiohttp.ClientError, PyMongoError, TimeoutError) as exc:
        raise IntegrationError(503, "Discord authorization unavailable") from exc

    _require_connected(bot, guild_id)
    if (
        not isinstance(channel, discord.TextChannel)
        or channel.type != discord.ChannelType.text
        or channel.guild.id != guild_id
        or channel.id != channel_id
        or guild.id != guild_id
        or member.id != owner_id
    ):
        raise IntegrationError(403, "Channel access denied")

    # The fetched channel can reference the gateway's cached guild. Rebind this
    # newly fetched object only, so permissions_for resolves fresh role flags.
    channel.guild = guild
    storyteller_role = vguild.settings.storyteller_role if vguild is not None else None
    if not eligible(member, channel, storyteller_role):
        raise IntegrationError(403, "Channel access denied")
