"""Tests for bot event handlers and guild cache integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from services import guild_cache

# Fixtures


@pytest.fixture(autouse=True, scope="function")
async def setup_guild_cache():
    """Set up guild cache with in-memory database for each test."""
    # Patch GUILD_CACHE_LOC to use in-memory database
    with patch("config.GUILD_CACHE_LOC", "file::memory:?cache=shared"):
        # Reinitialize the guild_cache instance with new location
        guild_cache.location = "file::memory:?cache=shared"
        guild_cache._initialized = False
        guild_cache._refreshed = False

        await guild_cache.initialize()
        yield guild_cache

        if guild_cache.initialized:
            await guild_cache.close()


@pytest.fixture
def mock_bot():
    """Create a mock InconnuBot instance."""
    bot = MagicMock(spec=InconnuBot)
    bot.guilds = []
    return bot


def make_mock_guild(guild_id: int, name: str, members: list | None = None) -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.icon = None
    guild.chunked = True
    guild.members = members or []
    return guild


def make_mock_member(
    member_id: int, guild: discord.Guild | None, name: str = "Test User"
) -> MagicMock:
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = member_id
    member.guild = guild
    member.name = name
    member.display_name = name
    member.display_avatar.url = "http://avatar.png"
    member.guild_avatar = None
    return member


async def mark_cache_ready():
    """Mark cache as ready by calling refresh."""
    guild_cache._refreshed = True


# Guild event tests


async def test_on_guild_join_before_ready(mock_bot):
    """Guild not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")

    # Simulate on_guild_join before ready
    with (
        patch("inconnu.stats.guild_joined", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_join(mock_bot, guild)

    # Cache should not have the guild
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_join_after_ready(mock_bot):
    """Guild added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild  # Fix circular ref

    # Mark cache as ready
    await mark_cache_ready()

    # Simulate on_guild_join after ready
    with (
        patch("inconnu.stats.guild_joined", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_join(mock_bot, guild)

    # Cache should have the guild
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is not None
    assert cached_guild.id == guild.id
    assert cached_guild.name == guild.name


async def test_on_guild_remove_before_ready(mock_bot):
    """Guild removal is no-op when cache not ready (no pre-existing data)."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_guild_remove before ready
    with (
        patch("inconnu.stats.guild_left", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_remove(mock_bot, guild)

    # Guild should not be in cache
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_remove_after_ready(mock_bot):
    """Guild removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild

    # Add guild to cache and mark ready
    await guild_cache.upsert_guilds(guild)
    await mark_cache_ready()

    # Simulate on_guild_remove after ready
    with (
        patch("inconnu.stats.guild_left", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_remove(mock_bot, guild)

    # Guild should be removed from cache
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_update_before_ready(mock_bot):
    """Guild update is no-op when cache not ready."""
    guild_before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    guild_before.members[0].guild = guild_before
    guild_after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])
    guild_after.members[0].guild = guild_after

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_guild_update before ready (cache not refreshed yet)
    with patch("inconnu.stats.guild_renamed", new_callable=AsyncMock):
        await InconnuBot.on_guild_update(guild_before, guild_after)

    # Guild should not be in cache at all
    cached_guild = await guild_cache.fetchguild(guild_after.id)
    assert cached_guild is None


async def test_on_guild_update_after_ready(mock_bot):
    """Guild updated in cache after ready."""
    guild_before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    guild_before.members[0].guild = guild_before
    guild_after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])
    guild_after.members[0].guild = guild_after

    # Add guild to cache with old name and mark ready
    await guild_cache.upsert_guilds(guild_before)
    await mark_cache_ready()

    # Simulate on_guild_update after ready
    with patch("inconnu.stats.guild_renamed", new_callable=AsyncMock):
        await InconnuBot.on_guild_update(guild_before, guild_after)

    # Cache should have new name
    cached_guild = await guild_cache.fetchguild(guild_after.id)
    assert cached_guild is not None
    assert cached_guild.name == "New Name"


# Member event tests


async def test_on_member_join_before_ready(mock_bot):
    """Member not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Simulate on_member_join before ready
    with patch("services.char_mgr.mark_active", new_callable=AsyncMock):
        await InconnuBot.on_member_join(member)

    # Member should not be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_join_after_ready(mock_bot):
    """Member added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Add guild to cache and mark ready
    await guild_cache.upsert_guilds(guild)
    await mark_cache_ready()

    # Simulate on_member_join after ready
    with patch("services.char_mgr.mark_active", new_callable=AsyncMock):
        await InconnuBot.on_member_join(member)

    # Member should be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is not None
    assert cached_member.id == member.id


async def test_on_member_remove_before_ready(mock_bot):
    """Member removal is no-op when cache not ready (no pre-existing data)."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_member_remove before ready
    with patch("services.char_mgr.mark_inactive", new_callable=AsyncMock):
        await InconnuBot.on_member_remove(member)

    # Member should not be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_remove_after_ready(mock_bot):
    """Member removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Add guild and member to cache, mark ready
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(member)
    await mark_cache_ready()

    # Simulate on_member_remove after ready
    with patch("services.char_mgr.mark_inactive", new_callable=AsyncMock):
        await InconnuBot.on_member_remove(member)

    # Member should be removed from cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_update_before_ready(mock_bot):
    """Member update is no-op when cache not ready."""
    guild = make_mock_guild(1, "Test Guild")
    member_before = make_mock_member(100, guild, "Old Name")
    member_after = make_mock_member(100, guild, "New Name")

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_member_update before ready (cache not refreshed)
    await InconnuBot.on_member_update(mock_bot, member_before, member_after)

    # Member should not be in cache at all
    cached_member = await guild_cache.fetchmember(guild.id, member_after.id)
    assert cached_member is None


async def test_on_member_update_after_ready(mock_bot):
    """Member updated in cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member_before = make_mock_member(100, guild, "Old Name")
    member_after = make_mock_member(100, guild, "New Name")

    # Add guild and member to cache, mark ready
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(member_before)
    await mark_cache_ready()

    # Simulate on_member_update after ready
    await InconnuBot.on_member_update(mock_bot, member_before, member_after)

    # Cache should have new name
    cached_member = await guild_cache.fetchmember(guild.id, member_after.id)
    assert cached_member is not None
    assert cached_member.name == "New Name"
