"""Tests for utils/permissions.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from config import settings
from models import VGuild
from models.vguild import VGuildSettings
from tests.mocks import MockMember
from utils.permissions import has_supporter_role, is_admin, is_storyteller


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


ST_ROLE = 1234


def make_storyteller(*, admin: bool = False, roles: list[int] | None = None) -> MockMember:
    """A member with the given admin status and roles."""
    roles = roles or []
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(administrator=admin)
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if role_id in roles else None
    )
    return member


def mock_vguild(storyteller_role: int | None) -> AsyncMock:
    """Patch VGuild.get_or_fetch to return a guild with the given Storyteller role."""
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
