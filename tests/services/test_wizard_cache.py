"""Basic WizardCache and CharacterGuild tests."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import Guild

import services
from services.guildcache import GuildCache
from services.wizard import CharacterGuild, WizardCache, WizardData

USER = 2


@pytest.fixture
def guild() -> Guild:
    guild = MagicMock(spec=Guild)
    guild.id = 1
    guild.name = "Test Guild"
    guild.icon.url = "https://example.com/guild.png"

    return guild


@pytest.fixture
def uk(guild: Guild) -> tuple[int, int]:
    return (guild.id, USER)


@pytest.fixture
def wc() -> WizardCache:
    return WizardCache()


def test_registration(wc: WizardCache, guild: Guild, uk: tuple[int, int]):
    key = wc.register(guild, USER, False)
    assert key in wc.cache
    assert uk in wc.users
    assert isinstance(wc.get(key), WizardData)


def test_anti_spam(wc: WizardCache, guild: Guild):
    key1 = wc.register(guild, USER, False)
    key2 = wc.register(guild, USER, False)
    assert key1 == key2

    key3 = wc.register(guild, USER, True)
    assert key3 != key1

    guild.id = 5
    key4 = wc.register(guild, USER, False)
    assert key4 != key1 and key4 != key3

    assert wc.count == 3


def test_delete(wc: WizardCache, guild: Guild, uk: tuple[int, int]):
    key = wc.register(guild, USER, False)
    wc.delete(key)
    assert key not in wc.cache
    assert uk not in wc.users


@pytest.fixture
async def guild_cache() -> AsyncGenerator[GuildCache]:
    """A real, empty GuildCache installed as the service."""
    cache = GuildCache(":memory:")
    await cache.initialize()
    with patch.object(services, "guild_cache", cache):
        yield cache
    await cache.close()


async def test_fetch_cached_guild(guild_cache: GuildCache, guild: Guild):
    """A cached guild's data is returned without a character count."""
    await guild_cache.upsert_guilds(guild)

    fetched = await CharacterGuild.fetch(guild.id)

    assert fetched == CharacterGuild(
        id=str(guild.id),
        name=guild.name,
        icon="https://example.com/guild.png",
        count=None,
    )


async def test_fetch_skips_members(guild_cache: GuildCache, guild: Guild):
    """Fetching a guild doesn't load its members."""
    await guild_cache.upsert_guilds(guild)

    with patch.object(guild_cache, "fetchmembers", new_callable=AsyncMock) as fetchmembers:
        await CharacterGuild.fetch(guild.id)

    fetchmembers.assert_not_awaited()


async def test_fetch_guild_bot_left(guild_cache: GuildCache, guild: Guild):
    """A guild the bot left is unknown, though its characters may remain."""
    await guild_cache.upsert_guilds(guild)
    await guild_cache.delete_guild(guild)

    assert await CharacterGuild.fetch(guild.id) == CharacterGuild.unknown(guild.id)


async def test_fetch_propagates_cache_errors():
    """Cache failures aren't disguised as an unknown guild."""
    with patch.object(services, "guild_cache", GuildCache(":memory:")):
        with pytest.raises(RuntimeError):
            await CharacterGuild.fetch(1)
