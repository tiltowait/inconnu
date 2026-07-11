"""Character transfer command tests."""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import errors
import services
from bot import InconnuBot
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
async def mock_fetchone(char: VChar) -> AsyncGenerator[AsyncMock, None]:
    """char_mgr.fetchone(), patched to return the char fixture."""
    with patch.object(services.char_mgr, "fetchone", new_callable=AsyncMock) as mock:
        mock.return_value = char
        yield mock


@pytest.fixture
async def mock_transfer() -> AsyncGenerator[AsyncMock, None]:
    """char_mgr.transfer(), patched."""
    with patch.object(services.char_mgr, "transfer", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_transfer_premium(bot: InconnuBot) -> AsyncGenerator[AsyncMock, None]:
    """InconnuBot.transfer_premium(), patched on the test bot instance."""
    with patch.object(bot, "transfer_premium", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_error() -> AsyncGenerator[AsyncMock, None]:
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
    assert "can't be the same" in str(mock_error.await_args.args[1])
    mock_fetchone.assert_not_awaited()


async def test_transfer_success(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_transfer_premium: AsyncMock,
    mock_respond: AsyncMock,
):
    """A valid transfer updates ownership, responds, and checks premium status."""
    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_transfer.assert_awaited_once_with(char, current_owner, new_owner)

    mock_respond.assert_awaited_once()
    message = mock_respond.await_args.args[0]
    assert char.name in message
    assert current_owner.mention in message
    assert new_owner.mention in message

    mock_transfer_premium.assert_awaited_once_with(new_owner, char)


async def test_transfer_duplicate_name_rejected(
    ctx: AppCtx,
    char: VChar,
    current_owner: discord.Member,
    new_owner: discord.Member,
    mock_fetchone: AsyncMock,
    mock_transfer: AsyncMock,
    mock_transfer_premium: AsyncMock,
    mock_respond: AsyncMock,
    mock_error: AsyncMock,
):
    """A DuplicateCharacterError from the manager is shown as an error embed."""
    mock_transfer.side_effect = errors.DuplicateCharacterError(
        f"{new_owner.display_name} already has a character named {char.name}"
    )

    await transfer_character(ctx, current_owner, char.name, new_owner)

    mock_error.assert_awaited_once()
    assert "already has a character named" in str(mock_error.await_args.args[1])
    mock_respond.assert_not_awaited()
    mock_transfer_premium.assert_not_awaited()


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
    assert "Character not found." in str(mock_error.await_args.args[1])
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
    assert "doesn't own" in str(mock_error.await_args.args[1])
    mock_transfer.assert_not_awaited()
