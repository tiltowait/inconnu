"""Tests for interface/premium.py's supporter role listeners."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from config import settings
from interface.premium import PremiumCog
from services import premium

UPLOAD_MENTION = "</character image upload:1>"


def make_member(*, supporter: bool, guild_id: int = settings.supporter_guild) -> MagicMock:
    """A member of the given guild, with or without the supporter role."""
    member = MagicMock(spec=discord.Member)
    member.configure_mock(id=1, name="Member")
    member.guild.id = guild_id
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if supporter and role_id == settings.supporter_role else None
    )
    return member


@pytest.fixture
def cog() -> PremiumCog:
    """A PremiumCog on a mock bot."""
    bot = MagicMock(spec=InconnuBot)
    bot.cmd_mention.return_value = UPLOAD_MENTION
    return PremiumCog(bot)


@pytest.fixture
async def mock_lost() -> AsyncGenerator[AsyncMock, None]:
    """premium.mark_lost(), patched."""
    with patch.object(premium, "mark_lost", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_gained() -> AsyncGenerator[AsyncMock, None]:
    """premium.mark_gained(), patched."""
    with patch.object(premium, "mark_gained", new_callable=AsyncMock) as mock:
        yield mock


async def test_role_gained(cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock):
    """Gaining the supporter role grants premium."""
    after = make_member(supporter=True)
    await PremiumCog.on_member_update(cog, make_member(supporter=False), after)

    mock_gained.assert_awaited_once_with(after, UPLOAD_MENTION)
    mock_lost.assert_not_awaited()


async def test_role_lost(cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock):
    """Losing the supporter role revokes premium."""
    after = make_member(supporter=False)
    await PremiumCog.on_member_update(cog, make_member(supporter=True), after)

    mock_lost.assert_awaited_once_with(after)
    mock_gained.assert_not_awaited()


@pytest.mark.parametrize("supporter", [True, False])
async def test_role_unchanged(
    cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock, supporter: bool
):
    """Member updates that don't change the role do nothing."""
    member = make_member(supporter=supporter)
    await PremiumCog.on_member_update(cog, member, member)

    mock_lost.assert_not_awaited()
    mock_gained.assert_not_awaited()


async def test_other_guild_ignored(cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock):
    """Role changes outside the supporter guild do nothing."""
    before = make_member(supporter=True, guild_id=settings.supporter_guild + 1)
    after = make_member(supporter=False, guild_id=settings.supporter_guild + 1)

    await PremiumCog.on_member_update(cog, before, after)
    await PremiumCog.on_member_join(cog, before)
    await PremiumCog.on_member_remove(cog, before)

    mock_lost.assert_not_awaited()
    mock_gained.assert_not_awaited()


async def test_supporter_joins(cog: PremiumCog, mock_gained: AsyncMock):
    """A supporter (re)joining the supporter guild regains premium."""
    member = make_member(supporter=True)
    await PremiumCog.on_member_join(cog, member)

    mock_gained.assert_awaited_once_with(member, UPLOAD_MENTION)


async def test_supporter_leaves(cog: PremiumCog, mock_lost: AsyncMock):
    """A supporter leaving the supporter guild loses premium."""
    member = make_member(supporter=True)
    await PremiumCog.on_member_remove(cog, member)

    mock_lost.assert_awaited_once_with(member)


async def test_non_supporter_join_and_leave(
    cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock
):
    """Non-supporters joining or leaving do nothing."""
    member = make_member(supporter=False)
    await PremiumCog.on_member_join(cog, member)
    await PremiumCog.on_member_remove(cog, member)

    mock_lost.assert_not_awaited()
    mock_gained.assert_not_awaited()
