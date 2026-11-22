"""Tests for interface/premium.py's supporter role listeners."""

from collections.abc import AsyncGenerator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from config import settings
from interface.premium import PremiumCog
from services import premium
from tests.mocks import MockMember

USER_ID = 1

type MockRemoveEvent = MagicMock
type MockUpdateEvent = MagicMock


def make_member(*, guild_id=settings.supporter_guild) -> MockMember:
    """A member of the given guild."""
    member = MagicMock(spec=discord.Member)
    member.configure_mock(id=USER_ID, name="Member")
    member.guild.id = guild_id
    return member


def update_event(*, supporter: bool, guild_id=settings.supporter_guild) -> MockUpdateEvent:
    """A member update whose roles include the supporter role, or don't. The
    gateway sends role IDs as strings."""
    roles = [str(settings.supporter_role)] if supporter else []
    payload = MagicMock(spec=discord.RawMemberUpdateEvent)
    payload.guild_id = guild_id
    payload.user_id = USER_ID
    payload.data = {"roles": [*roles, "777"]}
    payload.member = make_member(guild_id=guild_id)
    return payload


def remove_event(*, guild_id=settings.supporter_guild) -> MockRemoveEvent:
    """A user leaving the guild."""
    payload = MagicMock(spec=discord.RawMemberRemoveEvent)
    payload.guild_id = guild_id
    payload.user = MagicMock(spec=discord.User)
    payload.user.id = USER_ID
    return payload


@pytest.fixture(autouse=True)
def supporters() -> Iterator[set[int]]:
    """The supporter set, empty for each test."""
    with patch.object(premium, "_supporters", set()) as supporters:
        yield supporters


@pytest.fixture
def cog() -> PremiumCog:
    """A PremiumCog on a mock bot."""
    return PremiumCog(MagicMock(spec=InconnuBot))


@pytest.fixture
async def mock_lost() -> AsyncGenerator[AsyncMock]:
    """premium.mark_lost(), patched."""
    with patch.object(premium, "mark_lost", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_gained() -> AsyncGenerator[AsyncMock]:
    """premium.mark_gained(), patched."""
    with patch.object(premium, "mark_gained", new_callable=AsyncMock) as mock:
        yield mock


async def test_role_gained(cog: PremiumCog, mock_lost: AsyncMock, mock_gained: AsyncMock):
    """Gaining the supporter role grants premium."""
    payload = update_event(supporter=True)
    await PremiumCog.on_raw_member_update(cog, payload)

    mock_gained.assert_awaited_once_with(payload.member, cog.bot)
    mock_lost.assert_not_awaited()


async def test_role_lost(
    cog: PremiumCog, supporters: set[int], mock_lost: AsyncMock, mock_gained: AsyncMock
):
    """Losing the supporter role revokes premium."""
    supporters.add(USER_ID)
    payload = update_event(supporter=False)
    await PremiumCog.on_raw_member_update(cog, payload)

    mock_lost.assert_awaited_once_with(payload.member)
    mock_gained.assert_not_awaited()


@pytest.mark.parametrize("supporter", [True, False])
async def test_role_unchanged(
    cog: PremiumCog,
    supporters: set[int],
    mock_lost: AsyncMock,
    mock_gained: AsyncMock,
    supporter: bool,
):
    """Member updates that don't change the role do nothing."""
    if supporter:
        supporters.add(USER_ID)
    await PremiumCog.on_raw_member_update(cog, update_event(supporter=supporter))

    mock_lost.assert_not_awaited()
    mock_gained.assert_not_awaited()


async def test_other_guild_ignored(
    cog: PremiumCog, supporters: set[int], mock_lost: AsyncMock, mock_gained: AsyncMock
):
    """Role changes outside the supporter guild do nothing."""
    supporters.add(USER_ID)
    other = settings.supporter_guild + 1

    await PremiumCog.on_raw_member_update(cog, update_event(supporter=False, guild_id=other))
    await PremiumCog.on_raw_member_remove(cog, remove_event(guild_id=other))

    mock_lost.assert_not_awaited()
    mock_gained.assert_not_awaited()


async def test_supporter_leaves(cog: PremiumCog, supporters: set[int], mock_lost: AsyncMock):
    """A supporter leaving the supporter guild loses premium."""
    supporters.add(USER_ID)
    payload = remove_event()
    await PremiumCog.on_raw_member_remove(cog, payload)

    mock_lost.assert_awaited_once_with(payload.user)


async def test_non_supporter_leaves(cog: PremiumCog, mock_lost: AsyncMock):
    """Non-supporters leaving do nothing."""
    await PremiumCog.on_raw_member_remove(cog, remove_event())

    mock_lost.assert_not_awaited()
