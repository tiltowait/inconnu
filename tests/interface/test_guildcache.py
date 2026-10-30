"""Tests for interface/guildcache.py's guild cache syncing."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from interface.guildcache import GuildCacheCog
from services import guild_cache

# Fixtures


@pytest.fixture(autouse=True)
async def setup_guild_cache() -> AsyncGenerator[None, None]:
    """Set up guild cache with in-memory database for each test."""
    guild_cache.location = "file::memory:?cache=shared"
    guild_cache._initialized = False
    guild_cache._refreshed = False

    await guild_cache.initialize()
    yield

    if guild_cache.initialized:
        await guild_cache.close()


@pytest.fixture
def cog() -> GuildCacheCog:
    """A GuildCacheCog on a mock bot."""
    bot = MagicMock(spec=InconnuBot)
    bot.guilds = []
    return GuildCacheCog(bot)


def make_mock_guild(guild_id: int, name: str, members: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.icon = None
    guild.chunked = True
    guild.members = members or []
    for member in guild.members:
        member.guild = guild
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


def mark_cache_ready():
    """Mark the cache as ready, as if it had been refreshed."""
    guild_cache._refreshed = True


# Ready


async def test_on_ready_refreshes_once(cog: GuildCacheCog):
    """The cache is populated on the first ready only, not on reconnects."""
    with patch.object(guild_cache, "refresh", new_callable=AsyncMock) as mock_refresh:
        await cog.on_ready()
        await cog.on_ready()

    mock_refresh.assert_awaited_once_with(cog.bot.guilds)


# Guild events


async def test_on_guild_join_before_ready(cog: GuildCacheCog):
    """Guild not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")
    await cog.on_guild_join(guild)

    assert await guild_cache.fetchguild(guild.id) is None


async def test_on_guild_join_after_ready(cog: GuildCacheCog):
    """Guild added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    mark_cache_ready()

    await cog.on_guild_join(guild)

    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is not None
    assert cached_guild.id == guild.id
    assert cached_guild.name == guild.name


async def test_on_guild_remove_before_ready(cog: GuildCacheCog):
    """Guild removal is a no-op when the cache isn't ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    await cog.on_guild_remove(guild)

    assert await guild_cache.fetchguild(guild.id) is None


async def test_on_guild_remove_after_ready(cog: GuildCacheCog):
    """Guild removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    await guild_cache.upsert_guilds(guild)
    mark_cache_ready()

    await cog.on_guild_remove(guild)

    assert await guild_cache.fetchguild(guild.id) is None


async def test_on_guild_update_before_ready(cog: GuildCacheCog):
    """Guild update is a no-op when the cache isn't ready."""
    before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])

    await cog.on_guild_update(before, after)

    assert await guild_cache.fetchguild(after.id) is None


async def test_on_guild_update_after_ready(cog: GuildCacheCog):
    """Guild updated in cache after ready."""
    before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])
    await guild_cache.upsert_guilds(before)
    mark_cache_ready()

    await cog.on_guild_update(before, after)

    cached_guild = await guild_cache.fetchguild(after.id)
    assert cached_guild is not None
    assert cached_guild.name == "New Name"


# Member events


async def test_on_member_join_before_ready(cog: GuildCacheCog):
    """Member not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    await cog.on_member_join(member)

    assert await guild_cache.fetchmember(guild.id, member.id) is None


async def test_on_member_join_after_ready(cog: GuildCacheCog):
    """Member added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)
    await guild_cache.upsert_guilds(guild)
    mark_cache_ready()

    await cog.on_member_join(member)

    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is not None
    assert cached_member.id == member.id


async def test_on_member_remove_before_ready(cog: GuildCacheCog):
    """Member removal is a no-op when the cache isn't ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    await cog.on_member_remove(member)

    assert await guild_cache.fetchmember(guild.id, member.id) is None


async def test_on_member_remove_after_ready(cog: GuildCacheCog):
    """Member removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(member)
    mark_cache_ready()

    await cog.on_member_remove(member)

    assert await guild_cache.fetchmember(guild.id, member.id) is None


async def test_on_member_update_before_ready(cog: GuildCacheCog):
    """Member update is a no-op when the cache isn't ready."""
    guild = make_mock_guild(1, "Test Guild")
    before = make_mock_member(100, guild, "Old Name")
    after = make_mock_member(100, guild, "New Name")

    await cog.on_member_update(before, after)

    assert await guild_cache.fetchmember(guild.id, after.id) is None


async def test_on_member_update_after_ready(cog: GuildCacheCog):
    """Member updated in cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    before = make_mock_member(100, guild, "Old Name")
    after = make_mock_member(100, guild, "New Name")
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(before)
    mark_cache_ready()

    await cog.on_member_update(before, after)

    cached_member = await guild_cache.fetchmember(guild.id, after.id)
    assert cached_member is not None
    assert cached_member.name == "New Name"
