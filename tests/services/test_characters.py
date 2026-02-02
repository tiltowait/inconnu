"""Test character manager fetching."""

from unittest.mock import MagicMock

import discord
import pytest
import pytest_asyncio

import constants
import services
from errors import CharacterNotFoundError
from models import VChar

GUILD = 1
USER = 1
CHAR_NAME = "Test"
WRONG_GUILD = 2
WRONG_USER = 2


# Fixtures and factories


def mock_player(guild_id: int, user_id: int):
    """Create a mock Discord member."""
    player = MagicMock(spec=discord.Member)
    player.guild.id = guild_id
    player.id = user_id
    return player


def mock_bot_with_user(user_id: int, admin: bool):
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


@pytest_asyncio.fixture(scope="module")
async def char_id() -> str:
    """The ID of a dummy character inserted into the database."""
    splat = "vampire"
    char = VChar(
        guild=1,
        user=1,
        raw_name="Test",
        splat=splat,
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=splat == "vampire" and 1 or 0,
    )
    await char.save()
    yield char.id_str
    await char.delete()


@pytest.mark.parametrize(
    "user_id,admin,guild,exception",
    [
        (USER, False, GUILD, None),
        (WRONG_USER, False, GUILD, CharacterNotFoundError),
        (USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, True, GUILD, None),
        (WRONG_USER, True, WRONG_GUILD, LookupError),
        (USER, True, WRONG_GUILD, LookupError),
    ],
)
async def test_management(
    user_id: int,
    admin: bool,
    guild: int,
    exception: Exception,
    char_id: str,
):
    """Run a battery of CharManager tests."""
    mock_bot, user = mock_bot_with_user(user_id, admin)
    services.char_mgr.bot = mock_bot
    identifier = char_id if admin else CHAR_NAME

    if exception is not None:
        with pytest.raises(exception):
            _ = await services.char_mgr.fetchone(guild, user, identifier)
    else:
        char = await services.char_mgr.fetchone(guild, user, identifier)
        assert char is not None


# Tests for clear_caches()


@pytest_asyncio.fixture()
async def clear_manager_caches():
    """Clear the character manager caches before each test."""
    services.char_mgr.user_cache.clear()
    services.char_mgr.id_cache.clear()
    services.char_mgr.all_fetched.clear()
    yield


async def test_clear_caches_removes_from_both_caches(clear_manager_caches):
    """Test that clear_caches removes entries from both id_cache and user_cache."""
    # Create test characters
    char1 = VChar(
        guild=GUILD,
        user=USER,
        raw_name="Character1",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    char2 = VChar(
        guild=GUILD,
        user=USER,
        raw_name="Character2",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    await char1.save()
    await char2.save()

    try:
        # Fetch characters to populate cache
        await services.char_mgr.fetchall(GUILD, USER)

        # Verify characters are in cache
        key = f"{GUILD} {USER}"
        assert key in services.char_mgr.user_cache
        assert char1.id_str in services.char_mgr.id_cache
        assert char2.id_str in services.char_mgr.id_cache

        # Clear caches
        player = mock_player(GUILD, USER)
        services.char_mgr.clear_caches(player)

        # Verify caches are cleared
        assert key not in services.char_mgr.user_cache
        assert char1.id_str not in services.char_mgr.id_cache
        assert char2.id_str not in services.char_mgr.id_cache

    finally:
        await char1.delete()
        await char2.delete()


async def test_clear_caches_handles_empty_cache(clear_manager_caches):
    """Test that clear_caches handles the case where user has no cached characters."""
    player = mock_player(GUILD, 9999)

    # Should not raise an error
    services.char_mgr.clear_caches(player)

    # Verify nothing broke
    key = f"{GUILD} 9999"
    assert key not in services.char_mgr.user_cache


async def test_clear_caches_only_affects_specific_user(clear_manager_caches):
    """Test that clear_caches only clears the specified user's cache, not others."""
    other_user = 999

    # Create characters for two different users
    char1 = VChar(
        guild=GUILD,
        user=USER,
        raw_name="UserChar",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    char2 = VChar(
        guild=GUILD,
        user=other_user,
        raw_name="OtherChar",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    await char1.save()
    await char2.save()

    try:
        # Fetch both users' characters to populate cache
        await services.char_mgr.fetchall(GUILD, USER)
        await services.char_mgr.fetchall(GUILD, other_user)

        # Verify both are cached
        assert char1.id_str in services.char_mgr.id_cache
        assert char2.id_str in services.char_mgr.id_cache

        # Clear only USER's cache
        player = mock_player(GUILD, USER)
        services.char_mgr.clear_caches(player)

        # Verify USER's cache is cleared but other_user's is not
        assert char1.id_str not in services.char_mgr.id_cache
        assert char2.id_str in services.char_mgr.id_cache

        user_key = f"{GUILD} {USER}"
        other_key = f"{GUILD} {other_user}"
        assert user_key not in services.char_mgr.user_cache
        assert other_key in services.char_mgr.user_cache

    finally:
        await char1.delete()
        await char2.delete()


async def test_clear_caches_different_guilds(clear_manager_caches):
    """Test that clear_caches only affects the specified guild."""
    # Create character in two different guilds for same user
    char1 = VChar(
        guild=GUILD,
        user=USER,
        raw_name="GuildChar",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    char2 = VChar(
        guild=WRONG_GUILD,
        user=USER,
        raw_name="OtherGuildChar",
        splat="vampire",
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=1,
    )
    await char1.save()
    await char2.save()

    try:
        # Fetch characters in both guilds to populate cache
        await services.char_mgr.fetchall(GUILD, USER)
        await services.char_mgr.fetchall(WRONG_GUILD, USER)

        # Verify both are cached
        guild_key = f"{GUILD} {USER}"
        other_guild_key = f"{WRONG_GUILD} {USER}"
        assert guild_key in services.char_mgr.user_cache
        assert other_guild_key in services.char_mgr.user_cache

        # Clear only GUILD's cache
        player = mock_player(GUILD, USER)
        services.char_mgr.clear_caches(player)

        # Verify only GUILD's cache is cleared
        assert guild_key not in services.char_mgr.user_cache
        assert other_guild_key in services.char_mgr.user_cache

    finally:
        await char1.delete()
        await char2.delete()
