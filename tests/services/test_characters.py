"""Test character manager fetching."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import discord
import pytest
import pytest_asyncio

import constants
import services
from errors import CharacterNotFoundError, WrongGuild, WrongOwner
from models import VChar
from tests.mocks import MockMember

GUILD = 1
USER = 1
CHAR_NAME = "Test"
WRONG_GUILD = 2
WRONG_USER = 2

type MockBot = MagicMock


# Fixtures and factories


def mock_player(guild_id: int, user_id: int) -> MockMember:
    """Create a mock Discord member."""
    player = MagicMock(spec=discord.Member)
    player.guild.id = guild_id
    player.id = user_id
    return player


def mock_bot_with_user(user_id: int, admin: bool) -> tuple[MockBot, MockMember]:
    """Create a mock bot with user permissions."""
    # Create mock permissions
    mock_permissions = MagicMock(spec=discord.Permissions)
    mock_permissions.administrator = admin

    # Create mock user
    user = MagicMock(spec=discord.Member)
    user.id = user_id
    user.top_role.permissions = mock_permissions
    user.guild_permissions = mock_permissions

    # Create mock guild that returns the user
    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.get_member.return_value = user

    # Create mock bot that returns the guild
    mock_bot = MagicMock(spec=discord.AutoShardedBot)
    mock_bot.get_guild.return_value = mock_guild

    return mock_bot, user


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def char_id() -> AsyncGenerator[str]:
    """The ID of a dummy character inserted into the database."""
    splat = "vampire"
    char = VChar(
        guild=1,
        user=1,
        name="Test",
        splat=splat,
        humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=splat == "vampire" and 1 or 0,
    )
    await services.char_mgr.register(char)
    yield char.id_str
    await services.char_mgr.remove(char)


@pytest.mark.parametrize(
    "user_id,admin,guild,exception",
    [
        (USER, False, GUILD, None),
        (WRONG_USER, False, GUILD, CharacterNotFoundError),
        (USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, True, GUILD, None),
        (WRONG_USER, True, WRONG_GUILD, WrongGuild),
        (USER, True, WRONG_GUILD, WrongGuild),
    ],
)
async def test_management(
    user_id: int,
    admin: bool,
    guild: int,
    exception: type[Exception] | None,
    char_id: str,
):
    """Run a battery of CharManager tests."""
    _, user = mock_bot_with_user(user_id, admin)
    identifier = char_id if admin else CHAR_NAME

    if exception is not None:
        with pytest.raises(exception):
            _ = await services.char_mgr.fetchone(guild, user, identifier)
    else:
        char = await services.char_mgr.fetchone(guild, user, identifier)
        assert char is not None


async def test_fetchone_with_owner_id(char_id: str):
    """Plain guild and user IDs find the owner's character."""
    char = await services.char_mgr.fetchone(GUILD, USER, char_id)
    assert char.id_str == char_id


async def test_fetchone_with_non_owner_id(char_id: str):
    """A plain user ID can't be a Storyteller, so it can't reach another's character."""
    with pytest.raises(WrongOwner):
        await services.char_mgr.fetchone(GUILD, WRONG_USER, char_id)
