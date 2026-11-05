"""Tests for utils/permissions.py."""

from unittest.mock import MagicMock

import discord
import pytest

from config import settings
from tests.mocks import MockMember
from utils.permissions import has_supporter_role, is_admin


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
