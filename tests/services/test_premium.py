"""Tests for services/premium.py's supporter status tracking."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from config import settings
from services import premium
from tests.characters import gen_char


def make_member(*, supporter: bool = False) -> MagicMock:
    """A member who can be DMed."""
    member = MagicMock(spec=discord.Member)
    member.configure_mock(id=1, name="Supporter")
    member.send = AsyncMock()
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if supporter and role_id == settings.supporter_role else None
    )
    return member


@pytest.fixture
async def mock_update() -> AsyncGenerator[AsyncMock, None]:
    """db.supporters.update_one(), patched."""
    with patch("db.supporters.update_one", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_find() -> AsyncGenerator[AsyncMock, None]:
    """db.supporters.find_one(), patched to find no record."""
    with patch("db.supporters.find_one", new_callable=AsyncMock, return_value=None) as mock:
        yield mock


def recorded_discontinued(mock_update: AsyncMock) -> object:
    """The discontinued value written to the supporter record."""
    assert mock_update.await_args is not None
    return mock_update.await_args.args[1]["$set"]["discontinued"]


def sent_title(member: MagicMock) -> str | None:
    """The title of the embed DMed to the member."""
    return member.send.await_args.kwargs["embed"].title


def test_is_supporter():
    """Supporters are identified by the supporter role."""
    assert premium.is_supporter(make_member(supporter=True))
    assert not premium.is_supporter(make_member())


async def test_mark_lost(mock_update: AsyncMock):
    """Losing premium records the discontinuation date and DMs the member."""
    member = make_member()
    await premium.mark_lost(member)

    assert mock_update.await_args is not None
    assert mock_update.await_args.args[0] == {"_id": member.id}
    assert recorded_discontinued(mock_update) is not None
    assert sent_title(member) == "You are no longer a supporter!"


async def test_mark_gained(mock_update: AsyncMock):
    """Gaining premium clears the discontinuation date and points to the upload command."""
    member = make_member()
    await premium.mark_gained(member, "</character image upload:1>")

    assert recorded_discontinued(mock_update) is None
    assert sent_title(member) == "Thank you for your support!"
    embed = member.send.await_args.kwargs["embed"]
    assert "</character image upload:1>" in embed.description


async def test_dm_failure_is_ignored(mock_update: AsyncMock):
    """Members with closed DMs are still recorded."""
    member = make_member()
    member.send.side_effect = discord.Forbidden(MagicMock(status=403), "Closed DMs")

    await premium.mark_lost(member)

    mock_update.assert_awaited_once()


async def test_check_transfer_without_images(mock_update: AsyncMock, mock_find: AsyncMock):
    """Characters without images don't affect the new owner."""
    member = make_member()
    await premium.check_transfer(member, gen_char("vampire"))

    mock_find.assert_not_awaited()
    mock_update.assert_not_awaited()
    member.send.assert_not_awaited()


async def test_check_transfer_existing_record(mock_update: AsyncMock, mock_find: AsyncMock):
    """New owners with a supporter record are left alone."""
    mock_find.return_value = {"_id": 1, "discontinued": None}
    member = make_member()
    char = gen_char("vampire")
    char.profile.images.append("https://example.com/image.webp")

    await premium.check_transfer(member, char)

    mock_find.assert_awaited_once_with({"_id": member.id})
    mock_update.assert_not_awaited()
    member.send.assert_not_awaited()


async def test_check_transfer_no_record(mock_update: AsyncMock, mock_find: AsyncMock):
    """New owners without a record are marked as lapsed and warned."""
    member = make_member()
    char = gen_char("vampire")
    char.profile.images.append("https://example.com/image.webp")

    await premium.check_transfer(member, char)

    assert recorded_discontinued(mock_update) is not None
    title = sent_title(member)
    assert title is not None
    assert "transferred to you" in title
