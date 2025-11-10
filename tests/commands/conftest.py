"""Command test configurations and mocks."""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from inconnu.models.vchar import VChar


@pytest.fixture
def guild() -> discord.Guild:
    mock = AsyncMock(spec=discord.Guild)
    everyone_role = MagicMock(spec=discord.Role)
    mock.default_role = everyone_role
    mock.configure_mock(id=0, name="Test Guild")
    return mock


@pytest.fixture
def user() -> discord.Member:
    mock = AsyncMock(spec=discord.Member)
    mock.configure_mock(id=0, display_name="tiltowait", guild_avatar="https://example.com/img.png")
    return mock


@pytest.fixture
def bot() -> InconnuBot:
    bot = InconnuBot()

    return bot


@pytest.fixture
def ctx(bot: discord.Bot, guild: discord.Guild, user: discord.Member) -> AppCtx:
    response_mock = Mock(spec=discord.InteractionResponse)
    response_mock.configure_mock(is_done=Mock(return_value=False), defer=AsyncMock())
    perms = MagicMock(spec=discord.Permissions)
    type(perms).extternal_emojis = PropertyMock(return_value=True)
    channel = AsyncMock(spec=discord.TextChannel)
    channel.permissions_for.return_value = perms

    inter = AsyncMock(spec=discord.Interaction)
    inter.configure_mock(
        guild=guild,
        user=user,
        channel=channel,
        response=response_mock,
    )

    ctx = AppCtx(bot, inter)
    return ctx


@pytest.fixture
async def mock_respond() -> AsyncGenerator[AsyncMock, None]:
    with patch("ctx.AppCtx.respond", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_edit() -> AsyncGenerator[AsyncMock, None]:
    with patch("ctx.AppCtx.edit", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_delete() -> AsyncGenerator[AsyncMock, None]:
    with patch("ctx.AppCtx.delete", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_send_modal() -> AsyncGenerator[AsyncMock, None]:
    with patch("ctx.AppCtx.send_modal", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_is_done() -> AsyncGenerator[Mock, None]:
    with patch("discord.InteractionResponse.is_done") as mock:
        yield mock


@pytest.fixture
async def mock_defer() -> AsyncGenerator[AsyncMock, None]:
    with patch("discord.InteractionResponse.defer", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_save():
    with patch("inconnu.models.vchar.VChar.save", new_callable=AsyncMock) as mocked:
        yield mocked


@pytest.fixture
def char(guild: discord.Guild, user: discord.Member) -> VChar:
    char = VChar(
        guild=guild.id,
        user=user.id,
        name="Nadea Theron",
        splat="vampire",
        health="...........",
        willpower=".......",
        humanity=6,
        stains=0,
        potency=3,
    )
    return char


@pytest.fixture
def vamp(char) -> VChar:
    return char


@pytest.fixture
def thin_blood(char: VChar) -> VChar:
    char.splat = "thin-blood"
    return char


@pytest.fixture
def mortal(char: VChar) -> VChar:
    char.splat = "mortal"
    return char


@pytest.fixture
def ghoul(char: VChar) -> VChar:
    char.splat = "ghoul"
    return char


@pytest.fixture(autouse=True)
async def mock_emoji_manager():
    """Mock emoji manager to prevent initialization errors in tests."""
    # Create a mock that returns a placeholder emoji for any key
    mock_emojis = MagicMock()
    mock_emojis.__getitem__ = MagicMock(side_effect=lambda key: f":{key}:")
    mock_emojis.loaded = True

    with patch("inconnu.emojis", mock_emojis):
        yield mock_emojis
