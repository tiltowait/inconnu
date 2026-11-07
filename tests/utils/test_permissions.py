"""Tests for utils/permissions.py."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from discord.state import ConnectionState

from bot import InconnuBot
from config import settings
from ctx import AppCtx, AppInteraction
from models import VGuild
from models.vguild import VGuildSettings
from tests.mocks import MockMember
from utils.permissions import (
    get_or_fetch_supporter,
    has_supporter_role,
    is_admin,
    is_storyteller,
    is_supporter,
)

ST_ROLE = 1234

type MockBot = MagicMock
type MockGetOrFetch = AsyncMock


def make_member(*, supporter: bool = False) -> MockMember:
    """A member who may have the supporter role."""
    member = MagicMock(spec=discord.Member)
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if supporter and role_id == settings.supporter_role else None
    )
    return member


def test_has_supporter_role():
    """Supporters are identified by the supporter role."""
    assert has_supporter_role(make_member(supporter=True))
    assert not has_supporter_role(make_member())


@pytest.mark.parametrize("admin", [True, False])
def test_is_admin_member(admin: bool):
    """Members are admins when their server permissions include Administrator."""
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(administrator=admin)
    assert is_admin(member) is admin


def test_is_admin_outside_server():
    """Users outside a server (DMs) and missing users are never admins."""
    assert not is_admin(MagicMock(spec=discord.User))
    assert not is_admin(None)


def make_storyteller(*, admin: bool = False, roles: list[int] | None = None) -> MockMember:
    """A member with the given admin status and roles."""
    roles = roles or []
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(administrator=admin)
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if role_id in roles else None
    )
    return member


def mock_vguild(storyteller_role: int | None) -> MockGetOrFetch:
    """A replacement for VGuild.get_or_fetch, returning a guild with the given
    Storyteller role."""
    vguild = MagicMock(spec=VGuild)
    vguild.settings = VGuildSettings(storyteller_role=storyteller_role)
    return AsyncMock(return_value=vguild)


@pytest.mark.parametrize(
    "roles,storyteller_role,expected",
    [
        ([ST_ROLE], ST_ROLE, True),
        ([ST_ROLE + 1], ST_ROLE, False),
        ([ST_ROLE], None, False),
    ],
)
async def test_is_storyteller(roles: list[int], storyteller_role: int | None, expected: bool):
    """Holders of the server's Storyteller role are Storytellers."""
    member = make_storyteller(roles=roles)
    with patch.object(VGuild, "get_or_fetch", mock_vguild(storyteller_role)):
        assert await is_storyteller(member) is expected


async def test_is_storyteller_admin():
    """Admins are always Storytellers, without loading the server's settings."""
    fetch = mock_vguild(None)
    with patch.object(VGuild, "get_or_fetch", fetch):
        assert await is_storyteller(make_storyteller(admin=True))
    fetch.assert_not_awaited()


async def test_is_storyteller_outside_server():
    """Users outside a server are never Storytellers."""
    fetch = mock_vguild(ST_ROLE)
    with patch.object(VGuild, "get_or_fetch", fetch):
        assert not await is_storyteller(MagicMock(spec=discord.User))
        assert not await is_storyteller(None)
    fetch.assert_not_awaited()


def make_support_bot(member: MockMember | None) -> MockBot:
    """A bot whose support server has the given member."""
    guild = MagicMock(spec=discord.Guild)
    guild.get_member.return_value = member
    bot = MagicMock(spec=InconnuBot)
    bot.get_guild.return_value = guild
    return bot


def make_interaction(bot: MockBot) -> AppInteraction:
    """A real interaction, which has no attributes py-cord doesn't give it."""
    inter = object.__new__(discord.Interaction)
    inter._state = MagicMock(spec=ConnectionState)
    inter._state._get_client = MagicMock(return_value=bot)
    return cast(AppInteraction, inter)


@pytest.mark.parametrize("supporter", [True, False])
def test_is_supporter_with_ctx(supporter: bool):
    """Commands can check for supporters."""
    member = make_member(supporter=supporter)
    ctx = AppCtx(make_support_bot(member), MagicMock(spec=discord.Interaction))

    assert is_supporter(ctx, member) is supporter


@pytest.mark.parametrize("supporter", [True, False])
def test_is_supporter_with_interaction(supporter: bool):
    """Views and modals can check for supporters."""
    member = make_member(supporter=supporter)
    inter = make_interaction(make_support_bot(member))

    assert is_supporter(inter, member) is supporter


def test_is_supporter_not_on_support_server():
    """Someone who isn't on the support server isn't a supporter."""
    inter = make_interaction(make_support_bot(None))

    assert is_supporter(inter, make_member()) is False


def make_fetching_ctx(fetch_member: AsyncMock) -> AppCtx:
    """A ctx whose bot has to fetch the supporter guild from Discord."""
    guild = MagicMock(spec=discord.Guild)
    guild.fetch_member = fetch_member

    ctx = MagicMock(spec=AppCtx)
    ctx.bot = MagicMock(spec=InconnuBot)
    ctx.bot.get_guild.return_value = None
    ctx.bot.fetch_guild = AsyncMock(return_value=guild)
    return cast(AppCtx, ctx)


@pytest.mark.parametrize("supporter", [True, False])
async def test_get_or_fetch_supporter_fetches_member(supporter: bool):
    """Members missing from the cache are checked through the API."""
    member = make_member(supporter=supporter)
    ctx = make_fetching_ctx(AsyncMock(return_value=member))

    assert await get_or_fetch_supporter(ctx, member) is supporter


async def test_get_or_fetch_supporter_not_on_support_server():
    """Someone Discord can't find on the support server isn't a supporter."""
    response = MagicMock(spec=aiohttp.ClientResponse, status=404, reason="Not Found")
    error = discord.NotFound(response, "Unknown Member")
    ctx = make_fetching_ctx(AsyncMock(side_effect=error))

    assert await get_or_fetch_supporter(ctx, make_member()) is False
