"""Fresh authorization never relies on cached roles or channel overwrites."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from errors import IntegrationError
from models import VGuild
from models.vguild import VGuildSettings
from services.integration_access import authorize_channel, eligible
from utils.permissions import is_storyteller_role

GUILD = 100
CHANNEL = 200
OWNER = 300
ROLE = 400


@pytest.fixture
def access():
    """Prepare connected Discord snapshots and fresh settings."""
    bot = MagicMock(spec=InconnuBot)
    bot.is_ready.return_value = True
    bot.is_closed.return_value = False
    cached_guild = MagicMock(spec=discord.Guild)
    cached_guild.unavailable = False
    cached_guild.shard_id = 0
    bot.get_guild.return_value = cached_guild
    bot.get_shard.return_value.is_closed.return_value = False
    guild = MagicMock(spec=discord.Guild)
    guild.id = GUILD
    member = MagicMock(spec=discord.Member)
    member.id = OWNER
    member.guild = guild
    member.guild_permissions = discord.Permissions.none()
    member.get_role.return_value = MagicMock(spec=discord.Role)
    guild.fetch_member = AsyncMock(return_value=member)
    bot.fetch_guild = AsyncMock(return_value=guild)
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = CHANNEL
    channel.guild = cached_guild
    cached_guild.id = GUILD
    channel.type = discord.ChannelType.text
    channel.permissions_for.return_value = discord.Permissions(
        view_channel=True, read_message_history=True
    )
    bot.fetch_channel = AsyncMock(return_value=channel)
    vguild = MagicMock(spec=VGuild)
    vguild.settings = VGuildSettings(storyteller_role=ROLE)
    with patch.object(VGuild, "find_one", AsyncMock(return_value=vguild)) as settings:
        yield bot, guild, member, channel, settings


async def test_authorization_fetches_fresh_settings_member_and_channel(access):
    """Fetch current Discord objects and settings before granting access."""
    bot, guild, member, channel, settings = access
    await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    bot.fetch_guild.assert_awaited_once_with(GUILD)
    guild.fetch_member.assert_awaited_once_with(OWNER)
    bot.fetch_channel.assert_awaited_once_with(CHANNEL)
    settings.assert_awaited_once_with({"guild": GUILD})
    assert channel.guild is guild
    channel.permissions_for.assert_called_once_with(member)


async def test_role_removal_denies_cached_storyteller(access):
    """Deny access after the Storyteller role is removed."""
    bot, _, member, _, _ = access
    member.get_role.return_value = None
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_admin_is_eligible_without_storyteller_role(access):
    """Keep administrators eligible without a configured Storyteller role."""
    bot, _, member, _, settings = access
    member.guild_permissions = discord.Permissions(administrator=True)
    member.get_role.return_value = None
    settings.return_value = None
    await authorize_channel(bot, OWNER, GUILD, CHANNEL)


@pytest.mark.parametrize("permission", ["view_channel", "read_message_history"])
async def test_channel_access_required_even_for_storyteller(access, permission):
    """Require channel visibility and history access for Storytellers."""
    bot, _, _, channel, _ = access
    setattr(channel.permissions_for.return_value, permission, False)
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_wrong_guild_channel_denied(access):
    """Reject a channel belonging to another guild."""
    bot, _, _, channel, _ = access
    channel.guild.id = GUILD + 1
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


@pytest.mark.parametrize("channel_type", [discord.Thread, discord.VoiceChannel])
async def test_only_ordinary_text_channels_supported(access, channel_type):
    """Reject threads and voice channels."""
    bot, _, _, _, _ = access
    bot.fetch_channel.return_value = MagicMock(spec=channel_type)
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_announcement_channel_denied(access):
    """Reject announcement channels."""
    bot, _, _, channel, _ = access
    channel.type = discord.ChannelType.news
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_disconnected_shard_denied_even_if_ready(access):
    """Reject a closed shard despite the retained ready flag."""
    bot, _, _, _, _ = access
    bot.get_shard.return_value.is_closed.return_value = True
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 503
    bot.fetch_guild.assert_not_awaited()


async def test_disconnect_during_lookup_denied(access):
    """Reject a connection lost during Discord lookups."""
    bot, _, _, _, _ = access
    bot.is_ready.side_effect = [True, False]
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 503


async def test_timeout_fails_closed(access):
    """Return unavailable when fresh authorization times out."""
    bot, _, _, _, _ = access
    bot.fetch_guild.side_effect = TimeoutError
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 503


async def test_guild_missing_denied(access):
    """Reject a guild no longer shared with the bot."""
    bot, _, _, _, _ = access
    bot.get_guild.return_value = None
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_wrong_exact_channel_denied(access):
    """Reject another channel in the same guild."""
    bot, _, _, channel, _ = access
    channel.id = CHANNEL + 1
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


async def test_changed_storyteller_configuration_denied(access):
    """Honor fresh Storyteller configuration changes."""
    bot, _, member, _, settings = access
    settings.return_value.settings.storyteller_role = ROLE + 1
    member.get_role.side_effect = lambda role: (
        None if role != ROLE else MagicMock(spec=discord.Role)
    )
    with pytest.raises(IntegrationError) as exc:
        await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403


def real_guild(*, readable=True, admin=False):
    """Build real Pycord roles for permission regression checks."""
    state = MagicMock()
    state.store_user.return_value = MagicMock(id=OWNER)
    permissions = discord.Permissions(view_channel=readable, read_message_history=readable)
    roles = [
        {"id": str(GUILD), "name": "@everyone", "permissions": str(permissions.value)},
        {
            "id": str(ROLE),
            "name": "Storyteller",
            "position": 1,
            "permissions": str(discord.Permissions(administrator=admin).value),
        },
    ]
    for role in roles:
        role["colors"] = {"primary_color": 0}
    return discord.Guild(
        state=state,
        data={"id": str(GUILD), "name": "Guild", "owner_id": "999", "roles": roles},
    )


def real_channel(guild, *, deny_member_view=False):
    """Build real Pycord channel permission overwrites."""
    overwrites = []
    if deny_member_view:
        overwrites.append(
            {
                "id": str(OWNER),
                "type": 1,
                "allow": "0",
                "deny": str(discord.Permissions(view_channel=True).value),
            }
        )
    return discord.TextChannel(
        state=guild._state,
        guild=guild,
        data={
            "id": str(CHANNEL),
            "name": "rolls",
            "type": 0,
            "position": 0,
            "permission_overwrites": overwrites,
        },
    )


async def test_real_pycord_permissions_use_fresh_role_flags(access):
    """Resolve channel permission flags from the fresh guild snapshot."""
    bot, _, _, _, _ = access
    fresh = real_guild(readable=False)
    cached = real_guild(readable=True)
    channel = real_channel(cached)
    member = discord.Member(
        state=fresh._state, guild=fresh, data={"user": {}, "roles": [str(ROLE)]}
    )
    bot.fetch_guild.return_value = fresh
    bot.fetch_channel.return_value = channel
    with patch.object(discord.Guild, "fetch_member", AsyncMock(return_value=member)):
        with pytest.raises(IntegrationError) as exc:
            await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403
    assert channel.guild is fresh
    assert cached.default_role.permissions.view_channel


async def test_real_pycord_administrator_removal_takes_effect(access):
    """Reject removed administrators despite stale gateway roles."""
    bot, _, _, _, settings = access
    settings.return_value.settings.storyteller_role = None
    fresh = real_guild(admin=False)
    cached = real_guild(admin=True)
    member = discord.Member(
        state=fresh._state, guild=fresh, data={"user": {}, "roles": [str(ROLE)]}
    )
    bot.fetch_guild.return_value = fresh
    bot.fetch_channel.return_value = real_channel(cached)
    with patch.object(discord.Guild, "fetch_member", AsyncMock(return_value=member)):
        with pytest.raises(IntegrationError) as exc:
            await authorize_channel(bot, OWNER, GUILD, CHANNEL)
    assert exc.value.status == 403
    assert cached.get_role(ROLE).permissions.administrator


@pytest.mark.parametrize("denied", [False, True])
async def test_real_pycord_member_overwrite_preserved(access, denied):
    """Apply real Pycord member-specific channel overwrites."""
    bot, _, _, _, _ = access
    fresh = real_guild()
    member = discord.Member(
        state=fresh._state, guild=fresh, data={"user": {}, "roles": [str(ROLE)]}
    )
    bot.fetch_guild.return_value = fresh
    bot.fetch_channel.return_value = real_channel(real_guild(), deny_member_view=denied)
    with patch.object(discord.Guild, "fetch_member", AsyncMock(return_value=member)):
        if denied:
            with pytest.raises(IntegrationError) as exc:
                await authorize_channel(bot, OWNER, GUILD, CHANNEL)
            assert exc.value.status == 403
        else:
            await authorize_channel(bot, OWNER, GUILD, CHANNEL)


def test_shared_storyteller_predicate_handles_missing_and_nonmembers():
    """Users outside guilds cannot hold guild Storyteller authority."""
    assert not is_storyteller_role(None, ROLE)
    assert not is_storyteller_role(MagicMock(spec=discord.User), ROLE)


def test_eligible_rejects_member_from_another_guild(access):
    """Channel choices cannot cross the member's guild boundary."""
    _, _, member, channel, _ = access
    channel.guild.id = GUILD + 1
    assert eligible(member, channel, ROLE) is False
