"""Guild cache tests."""

from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from discord import Guild, Member

from services.guildcache import GuildCache
from utils.discord_helpers import get_avatar


def make_guild(id: int) -> Guild:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=Guild)
    guild.id = id
    guild.name = f"Test Guild {id}"
    guild.icon.url = f"https://example.com/g{id}.png"
    guild.members = []
    guild.member_count = 0

    return guild


def make_member(guild: Guild, id: int) -> Member:
    """Create a mock Discord member."""
    member = MagicMock(spec=Member)
    member.id = id
    member.guild = guild
    member.name = f"Member {id}"
    member.guild_avatar.url = f"https://example.com/m{id}.png"

    return member


@pytest.fixture
def g1() -> Guild:
    return make_guild(1)


@pytest.fixture
def g2() -> Guild:
    """Guild with three members."""
    guild = MagicMock(spec=Guild)
    guild.id = 2
    guild.name = "Test Guild 2"
    guild.icon.url = "https://example.com/g2.png"

    guild.members = [make_member(guild, n) for n in range(3)]
    guild.member_count = len(guild.members)

    return guild


@pytest.fixture
async def gce() -> AsyncGenerator[GuildCache, None]:
    """An empty GuildCache."""
    gc = GuildCache("file::memory:?cache=shared")
    await gc.initialize()
    yield gc
    await gc.close()


@pytest.fixture
async def gcf(gce: GuildCache, g1: Guild, g2: Guild) -> AsyncGenerator[GuildCache, None]:
    """A populated GuildCache."""
    await gce.upsert_guilds([g1, g2])
    yield gce


async def test_initialized():
    gc = GuildCache("file::memory:?cache=shared")
    assert not gc.initialized
    await gc.initialize()
    assert gc.initialized


async def test_uninitialized_operations_raise_error(g1: Guild):
    """Operations on uninitialized cache should raise RuntimeError."""
    gc = GuildCache("file::memory:?cache=shared")

    with pytest.raises(RuntimeError, match="not been initialized"):
        await gc.upsert_guilds(g1)

    with pytest.raises(RuntimeError, match="not been initialized"):
        await gc.fetchguild(1)


async def test_gc_not_ready(gce: GuildCache):
    """An empty cache is not ready."""
    assert not await gce.ready()


async def test_gc_ready(gcf: GuildCache):
    """A populated cache is ready."""
    assert await gcf.ready()


async def test_empty_guild_upsert(gce: GuildCache, g1: Guild):
    await gce.upsert_guilds(g1)
    guild = await gce.fetchguild(g1.id)
    assert guild is not None
    assert guild.id == g1.id
    assert guild.name == g1.name
    assert guild.icon == g1.icon.url  # type:ignore


async def test_full_guild_upsert(gce: GuildCache, g2: Guild):
    await gce.upsert_guilds(g2)
    m2 = g2.members[1]

    member = await gce.fetchmember(m2.guild.id, m2.id)
    assert member is not None
    assert member.id == m2.id
    assert member.name == m2.name
    assert member.icon == get_avatar(m2).url
    assert member.guild.id == g2.id


async def test_fetchguild_populates_members(gcf: GuildCache, g2: Guild):
    guild = await gcf.fetchguild(g2.id)
    assert guild is not None
    assert guild.id == g2.id
    assert len(guild.members) == g2.member_count


async def test_delete_guild(gcf: GuildCache, g2: Guild):
    members = await gcf.fetchmembers(g2.id)
    assert members is not None
    assert len(members) > 1

    await gcf.delete_guild(g2)
    members = await gcf.fetchmembers(g2.id)
    assert not members, "Deletion didn't cascade"


async def test_delete_member(gcf: GuildCache, g2: Guild):
    members = await gcf.fetchmembers(g2.id)
    assert members is not None
    before_count = len(members)

    await gcf.delete_member(g2.members[0])
    members = await gcf.fetchmembers(g2.id)
    assert len(members) == before_count - 1


async def test_update_guild(gcf: GuildCache, g1: Guild):
    g1.name = "Foo"
    g1.icon.url = "flip"  # type:ignore
    await gcf.upsert_guilds(g1)

    guild = await gcf.fetchguild(g1.id)
    assert guild is not None
    assert guild.name == "Foo"
    assert guild.icon == "flip"


async def test_upsert_member(gcf: GuildCache, g2: Guild):
    m1 = g2.members[0]
    m1.name = "Billy"
    m1.guild_avatar.url = "icon"  # type:ignore
    await gcf.upsert_members(m1)

    member = await gcf.fetchmember(m1.guild.id, m1.id)
    assert member is not None
    assert member.id == m1.id
    assert member.name == m1.name
    assert member.icon == get_avatar(m1).url


async def test_reset(gcf: GuildCache, g1: Guild, g2: Guild):
    await gcf.refresh([g1])
    assert not await gcf.fetchmembers(g2)

    guild = await gcf.fetchguild(g1.id)
    assert guild is not None
    assert guild.id == g1.id


async def test_fetchmember_nonexistent_guild(gce: GuildCache):
    """Fetching a member from a nonexistent guild returns None."""
    member = await gce.fetchmember(999, 123)
    assert member is None


async def test_fetchmembers_nonexistent_guild(gce: GuildCache):
    """Fetching members from a nonexistent guild returns empty list."""
    members = await gce.fetchmembers(999)
    assert members == []


async def test_guild_with_none_icon(gce: GuildCache):
    """Guilds with no icon should store None."""
    guild = MagicMock(spec=Guild)
    guild.id = 42
    guild.name = "No Icon Guild"
    guild.icon = None
    guild.members = []
    guild.member_count = 0

    await gce.upsert_guilds(guild)
    cached = await gce.fetchguild(42)

    assert cached is not None
    assert cached.id == 42
    assert cached.icon is None


async def test_reinitialize_existing_database(g1: Guild):
    """Re-initializing an existing database should be safe."""
    import os
    import tempfile

    # Use a real temp file instead of in-memory for this test
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        gc = GuildCache(path)
        await gc.initialize()
        await gc.upsert_guilds(g1)
        await gc.close()

        # Reinitialize the same database
        gc2 = GuildCache(path)
        await gc2.initialize()

        # Data should still be there
        guild = await gc2.fetchguild(g1.id)
        assert guild is not None
        assert guild.id == g1.id

        await gc2.close()
    finally:
        os.unlink(path)
