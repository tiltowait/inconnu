"""Character transfer command tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest

import errors
import services
from ctx import AppCtx
from inconnu.misc.transfer import transfer_character
from models.vchar import VChar


def make_member(member_id: int, name: str) -> discord.Member:
    """Create a Member mock."""
    member = MagicMock(spec=discord.Member)
    member.configure_mock(id=member_id, display_name=name, mention=f"<@{member_id}>")
    return member


@pytest.fixture
def current_owner() -> discord.Member:
    """The character's current owner (ID matches the char fixture's user)."""
    return make_member(0, "Current")


@pytest.fixture
def new_owner() -> discord.Member:
    """The transfer recipient."""
    return make_member(1, "Recipient")


@pytest.fixture
async def mock_fetchone(char: VChar) -> AsyncGenerator[AsyncMock]:
    """char_mgr.fetchone(), patched to return the char fixture."""
    with patch.object(services.char_mgr, "fetchone", new_callable=AsyncMock) as mock:
        mock.return_value = char
        yield mock


@pytest.fixture
async def mock_transfer() -> AsyncGenerator[AsyncMock]:
    """char_mgr.transfer(), patched."""
    with patch.object(services.char_mgr, "transfer", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_lapse_date() -> AsyncGenerator[AsyncMock]:
    """premium.lapse_date(), patched to say the new owner is a supporter."""
    with patch.object(services.premium, "lapse_date", autospec=True, return_value=None) as mock:
        yield mock


@pytest.fixture
async def mock_error() -> AsyncGenerator[AsyncMock]:
    """ui.embeds.error(), patched."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock:
        yield mock


async def test_transfer_same_owner_rejected(
    ctx: AppCtx,
    current_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_error: AsyncMock,
):
    """Transferring a character to its current owner fails before any lookup."""
    await transfer_character(ctx, current_owner, "Nadea Theron", current_owner)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    assert "can't be the same" in str(mock_error.await_args.args[1])
    mock_fetchone.assert_not_awaited()


async def test_transfer_success(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
    mock_respond: AsyncMock,
):
    """A valid transfer updates ownership and responds."""
    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_transfer.assert_awaited_once_with(char, current_owner, new_owner)

    mock_respond.assert_awaited_once()
    assert mock_respond.await_args is not None
    message = mock_respond.await_args.args[0]
    assert char.name in message
    assert current_owner.mention in message
    assert new_owner.mention in message


async def test_transfer_duplicate_name_rejected(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
    mock_respond: AsyncMock,
    mock_error: AsyncMock,
):
    """A DuplicateCharacterError from the manager is shown as an error embed."""
    mock_transfer.side_effect = errors.DuplicateCharacterError(
        f"{new_owner.display_name} already has a character named {char.name}"
    )

    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    assert "already has a character named" in str(mock_error.await_args.args[1])
    mock_respond.assert_not_awaited()
    mock_lapse_date.assert_not_awaited()


async def test_transfer_character_not_found(
    ctx: AppCtx,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_error: AsyncMock,
):
    """An unknown character name produces a not-found error."""
    mock_fetchone.side_effect = errors.CharacterNotFoundError("nope")

    await transfer_character(ctx, current_owner, "Jimmy Maxwell", new_owner)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    assert "Character not found." in str(mock_error.await_args.args[1])
    mock_transfer.assert_not_awaited()


@pytest.mark.parametrize("error", [errors.WrongGuild, errors.WrongOwner])
async def test_transfer_someone_elses_character(
    error: type[errors.CharacterError],
    ctx: AppCtx,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_error: AsyncMock,
):
    """A character ID belonging to someone else shows the reason."""
    mock_fetchone.side_effect = error("Not theirs")

    await transfer_character(ctx, current_owner, "507f1f77bcf86cd799439011", new_owner)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    assert "Not theirs" in str(mock_error.await_args.args[1])
    mock_transfer.assert_not_awaited()


@pytest.mark.parametrize("attr,value", [("user", 42), ("guild", 42)])
async def test_transfer_ownership_mismatch(
    attr: str,
    value: int,
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_error: AsyncMock,
):
    """A guild or owner mismatch on the fetched character blocks the transfer."""
    setattr(char, attr, value)

    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_error.assert_awaited_once()
    assert mock_error.await_args is not None
    assert "doesn't own" in str(mock_error.await_args.args[1])
    mock_transfer.assert_not_awaited()


def sent_description(member: discord.Member) -> str:
    """The description of the embed DMed to the member."""
    send = cast(AsyncMock, member.send)
    assert send.await_args is not None
    return send.await_args.kwargs["embed"].description


async def test_transfer_without_images(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
):
    """Characters without images don't affect the new owner."""
    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_lapse_date.assert_not_awaited()
    cast(AsyncMock, new_owner.send).assert_not_awaited()


async def test_transfer_images_to_supporter(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
):
    """Supporters inherit images without warning."""
    char.profile.images.append("https://example.com/image.webp")

    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_lapse_date.assert_awaited_once_with(new_owner.id)
    cast(AsyncMock, new_owner.send).assert_not_awaited()


@pytest.mark.parametrize(
    "lapsed,deadline",
    [
        (timedelta(0), "in 7 days"),
        (timedelta(days=3), "in 4 days"),
        (timedelta(days=6), "in 1 day"),
        (timedelta(days=6, hours=20), "within a day"),
    ],
)
async def test_transfer_images_to_non_supporter(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
    lapsed: timedelta,
    deadline: str,
):
    """Non-supporters are warned when their new character's images will be deleted."""
    char.profile.images.append("https://example.com/image.webp")
    mock_lapse_date.return_value = datetime.now(UTC) - lapsed

    await transfer_character(ctx, current_owner, char.name, new_owner)

    assert f"images will be deleted {deadline}" in sent_description(new_owner)


async def test_transfer_warning_dm_failure_ignored(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_lapse_date: AsyncMock,
):
    """Recipients with closed DMs don't break the transfer."""
    char.profile.images.append("https://example.com/image.webp")
    mock_lapse_date.return_value = datetime.now(UTC)
    response = MagicMock(spec=aiohttp.ClientResponse, status=403, reason="Forbidden")
    cast(AsyncMock, new_owner.send).side_effect = discord.Forbidden(response, "Closed DMs")

    await transfer_character(ctx, current_owner, char.name, new_owner)

    cast(AsyncMock, new_owner.send).assert_awaited_once()
