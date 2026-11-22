"""Tests for services/premium.py's supporter status tracking."""

from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from config import settings
from models import VChar
from services import premium
from tests.characters import gen_char
from tests.mocks import MockGuild, MockMember

type MockClient = MagicMock


def make_member(*, supporter=False, user_id=1) -> MockMember:
    """A member who can be DMed."""
    member = MagicMock(spec=discord.Member)
    member.configure_mock(id=user_id, name="Supporter")
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if supporter and role_id == settings.supporter_role else None
    )
    return member


@pytest.fixture(autouse=True)
def supporters() -> Iterator[set[int]]:
    """The supporter set, empty for each test."""
    with patch.object(premium, "_supporters", set()) as supporters:
        yield supporters


@pytest.fixture
async def mock_update() -> AsyncGenerator[AsyncMock]:
    """db.supporters.update_one(), patched."""
    with patch("db.supporters.update_one", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_find() -> AsyncGenerator[AsyncMock]:
    """db.supporters.find_one(), patched to find no record."""
    with patch("db.supporters.find_one", new_callable=AsyncMock, return_value=None) as mock:
        yield mock


def recorded_discontinued(mock_update: AsyncMock) -> object:
    """The discontinued value written to the supporter record."""
    assert mock_update.await_args is not None
    return mock_update.await_args.args[1]["$set"]["discontinued"]


def sent_title(member: MockMember) -> str | None:
    """The title of the embed DMed to the member."""
    return member.send.await_args.kwargs["embed"].title


def sent_description(member: MockMember) -> str:
    """The description of the embed DMed to the member."""
    return member.send.await_args.kwargs["embed"].description


def recorded_statuses(mock_update: AsyncMock) -> dict[int, bool]:
    """Whether each recorded user is a supporter, by user ID."""
    return {
        call.args[0]["_id"]: call.args[1]["$set"]["discontinued"] is None
        for call in mock_update.await_args_list
    }


def support_server(members: list[MockMember], *, has_role=True) -> MockGuild:
    """A fetched support server with the given members."""

    async def fetch_members(limit: int | None) -> AsyncIterator[MockMember]:
        """Yield the members."""
        for member in members:
            yield member

    guild = MagicMock(spec=discord.Guild)
    guild.get_role.return_value = MagicMock(spec=discord.Role) if has_role else None
    guild.fetch_members = fetch_members
    return guild


def make_client(guild: MockGuild) -> MockClient:
    """A client that fetches the given support server."""
    client = MagicMock(spec=discord.Client)
    client.fetch_guild.return_value = guild
    return client


def char_with_images() -> VChar:
    """A character with a profile image, already transferred to its new owner."""
    char = gen_char("vampire")
    char.raw_name = "Nadea"
    char.user = 1
    char.profile.images.append("https://example.com/image.webp")
    return char


async def test_mark_lost(mock_update: AsyncMock):
    """Losing premium records the discontinuation date and DMs the member."""
    member = make_member()
    await premium.mark_lost(member)

    assert mock_update.await_args is not None
    assert mock_update.await_args.args[0] == {"_id": member.id}
    assert recorded_discontinued(mock_update) is not None
    assert sent_title(member) == "You are no longer a supporter!"
    assert "within 7 days" in sent_description(member)


async def test_mark_gained(mock_update: AsyncMock):
    """Gaining premium clears the discontinuation date and points to the upload command."""
    member = make_member()
    await premium.mark_gained(member, "</character image upload:1>")

    assert recorded_discontinued(mock_update) is None
    assert sent_title(member) == "Thank you for your support!"
    embed = member.send.await_args.kwargs["embed"]
    assert "</character image upload:1>" in embed.description


async def test_marking_updates_supporters(mock_update: AsyncMock, supporters: set[int]):
    """Gaining and losing premium updates the supporter checks."""
    member = make_member()

    await premium.mark_gained(member, None)
    assert premium.is_supporter(member.id)

    await premium.mark_lost(member)
    assert not premium.is_supporter(member.id)
    assert not supporters


@pytest.mark.parametrize("gained", [True, False])
async def test_status_changes_before_write(mock_update: AsyncMock, gained: bool):
    """The supporter set changes before the write, so an event arriving
    during it doesn't repeat the change (and its DM)."""
    member = make_member()
    if not gained:
        await premium.mark_gained(member, None)

    seen: list[bool] = []
    mock_update.side_effect = lambda *_, **__: seen.append(premium.is_supporter(member.id))

    if gained:
        await premium.mark_gained(member, None)
    else:
        await premium.mark_lost(member)

    assert seen == [gained]


async def test_initialize(supporters: set[int]):
    """Supporters are loaded from records without a discontinuation date."""
    supporters.add(99)

    async def records() -> AsyncIterator[dict[str, int]]:
        """Yield the active supporters' records."""
        for user_id in (1, 2):
            yield {"_id": user_id}

    with patch("db.supporters.find", return_value=records()) as mock_find:
        await premium.initialize()

    assert supporters == {1, 2}
    assert mock_find.call_args.args[0] == {"discontinued": None}


async def test_sync(mock_update: AsyncMock, supporters: set[int]):
    """Syncing catches status changes missed while offline, without DMs."""
    supporters.update({1, 2})  # 2 has lapsed
    members = [
        make_member(supporter=True, user_id=1),
        make_member(supporter=True, user_id=3),  # New
        make_member(supporter=False, user_id=4),
    ]
    client = make_client(support_server(members))

    await premium.sync(client)

    assert supporters == {1, 3}
    assert recorded_statuses(mock_update) == {2: False, 3: True}
    client.fetch_guild.assert_awaited_once_with(settings.supporter_guild)
    for member in members:
        member.send.assert_not_awaited()


async def test_sync_without_supporter_role(mock_update: AsyncMock, supporters: set[int]):
    """A support server without the role doesn't revoke everyone's premium."""
    supporters.add(1)
    client = make_client(support_server([make_member(user_id=1)], has_role=False))

    await premium.sync(client)

    assert supporters == {1}
    mock_update.assert_not_awaited()


async def test_sync_keeps_changes_seen_meanwhile(mock_update: AsyncMock, supporters: set[int]):
    """A role change seen while the sync runs is newer than the sync's fetch."""
    member = make_member(user_id=5)

    async def fetch_members(limit: int | None) -> AsyncIterator[MockMember]:
        """Yield the member before their role arrives, then grant it."""
        yield member
        await premium.mark_gained(member, None)

    guild = support_server([])
    guild.fetch_members = fetch_members

    await premium.sync(make_client(guild))

    assert supporters == {5}
    assert recorded_statuses(mock_update) == {5: True}


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


async def test_check_transfer_stale_record(mock_update: AsyncMock, mock_find: AsyncMock):
    """Non-supporters whose record still says active are marked as lapsed."""
    mock_find.return_value = {"_id": 1, "discontinued": None}
    member = make_member()

    await premium.check_transfer(member, char_with_images())

    mock_find.assert_awaited_once_with({"_id": member.id})
    assert recorded_discontinued(mock_update) is not None
    assert "deleted in 7 days" in sent_description(member)


async def test_check_transfer_supporter_without_record(
    mock_update: AsyncMock, mock_find: AsyncMock, supporters: set[int]
):
    """Supporters without a record aren't marked as lapsed."""
    member = make_member()
    supporters.add(member.id)

    await premium.check_transfer(member, char_with_images())

    mock_find.assert_not_awaited()
    mock_update.assert_not_awaited()
    member.send.assert_not_awaited()


async def test_check_transfer_no_record(mock_update: AsyncMock, mock_find: AsyncMock):
    """New owners without a record are marked as lapsed and get the full grace period."""
    member = make_member()

    await premium.check_transfer(member, char_with_images())

    assert recorded_discontinued(mock_update) is not None
    assert sent_title(member) == "Nadea has profile images"
    assert "deleted in 7 days" in sent_description(member)


@pytest.mark.parametrize(
    "lapsed,deadline",
    [
        (timedelta(days=3), "in 4 days"),
        (timedelta(days=6), "in 1 day"),
        (timedelta(days=6, hours=20), "within a day"),
    ],
)
async def test_check_transfer_lapsed_supporter(
    mock_update: AsyncMock, mock_find: AsyncMock, lapsed: timedelta, deadline: str
):
    """Lapsed supporters keep their existing deadline, so transfers can't extend it."""
    # Mongo returns naive UTC datetimes
    discontinued = (datetime.now(UTC) - lapsed).replace(tzinfo=None)
    mock_find.return_value = {"_id": 1, "discontinued": discontinued}
    member = make_member()

    await premium.check_transfer(member, char_with_images())

    mock_update.assert_not_awaited()
    assert f"deleted {deadline}" in sent_description(member)
