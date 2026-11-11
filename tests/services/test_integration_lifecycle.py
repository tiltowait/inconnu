"""Departure revocation and thirty-day cleanup protect key lifecycle."""

from datetime import UTC, datetime, timedelta
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

import db
from bot import InconnuBot
from models import VChar
from services.integration_lifecycle import revoke_for_guild

NOW = datetime(2026, 11, 11, 12, tzinfo=UTC)
GUILD = 100
OWNER = 200


@pytest.fixture
async def database():
    """Isolate raw collections from the configured database."""
    database = AsyncMongoMockClient(tz_aware=True).integration_lifecycle_tests
    with (
        patch.object(db, "integration_keys", database.integration_keys),
        patch.object(db, "guilds", database.guilds),
    ):
        yield database


def key(*, guild=GUILD, owner=OWNER, **values):
    """Build an isolated key record with a permanent default expiry."""
    return {
        "_id": ObjectId(),
        "guild_id": guild,
        "owner_id": owner,
        "active": True,
        "expires_at": None,
        "revoked_at": None,
        **values,
    }


def departure(user=None):
    """Build a real raw departure payload without requiring a cached member."""
    data = {
        "guild_id": str(GUILD),
        "user": {
            "id": str(OWNER),
            "username": "former-owner",
            "discriminator": "0",
            "avatar": None,
        },
    }
    if user is None:
        user = discord.User(state=MagicMock(), data=data["user"])
    return discord.RawMemberRemoveEvent(data, user)


async def test_uncached_member_departure_revokes_only_own_guild_keys(database):
    """Leaving revokes permanent keys without touching other owners or guilds."""
    own = key()
    other_owner = key(owner=OWNER + 1)
    other_guild = key(guild=GUILD + 1)
    await database.integration_keys.insert_many([own, other_owner, other_guild])
    payload = departure()
    assert isinstance(payload.user, discord.User)
    assert not isinstance(payload.user, discord.Member)
    with patch("services.char_mgr.mark_inactive", new=AsyncMock()) as inactive:
        await InconnuBot.on_raw_member_remove(MagicMock(), payload)
    revoked = await database.integration_keys.find_one({"_id": own["_id"]})
    assert revoked["active"] is False
    assert isinstance(revoked["revoked_at"], datetime)
    assert revoked["expires_at"] is None
    assert (await database.integration_keys.find_one({"_id": other_owner["_id"]}))["active"]
    assert (await database.integration_keys.find_one({"_id": other_guild["_id"]}))["active"]
    inactive.assert_not_awaited()


async def test_rejoin_does_not_reactivate_departure_revoked_keys(database):
    """Rejoining restores characters without restoring a revoked permanent key."""
    row = key()
    await database.integration_keys.insert_one(row)
    member = MagicMock(id=OWNER)
    member.guild.id = GUILD
    with (
        patch("services.char_mgr.mark_inactive", new=AsyncMock()),
        patch("services.char_mgr.mark_active", new=AsyncMock()) as active,
    ):
        await InconnuBot.on_raw_member_remove(MagicMock(), departure())
        await InconnuBot.on_member_join(MagicMock(), member)
    stored = await database.integration_keys.find_one({"_id": row["_id"]})
    assert stored["active"] is False
    assert stored["revoked_at"] is not None
    active.assert_awaited_once_with(member)


async def test_guild_departure_revokes_all_owners_without_rewriting_prior_revocation(database):
    """Removing the bot revokes every guild key and preserves earlier timestamps."""
    old_revocation = NOW - timedelta(days=1)
    rows = [key(), key(owner=OWNER + 1), key(active=False, revoked_at=old_revocation)]
    other_guild = key(guild=GUILD + 1)
    await database.integration_keys.insert_many([*rows, other_guild])
    guild = MagicMock(id=GUILD)
    bot = MagicMock()
    bot._set_presence = AsyncMock()
    with patch("inconnu.stats.guild_left", new=AsyncMock()) as left:
        await InconnuBot.on_guild_remove(bot, guild)
    stored = await database.integration_keys.find({"guild_id": GUILD}).to_list(None)
    assert all(row["active"] is False and row["revoked_at"] is not None for row in stored)
    assert (await database.integration_keys.find_one({"_id": rows[2]["_id"]}))[
        "revoked_at"
    ] == old_revocation
    assert (await database.integration_keys.find_one({"_id": other_guild["_id"]}))["active"]
    left.assert_awaited_once_with(guild)
    bot._set_presence.assert_awaited_once()


async def test_repeated_departure_does_not_extend_retention(database):
    """Repeated events preserve the first revocation date."""
    old_revocation = NOW - timedelta(days=5)
    row = key(active=False, revoked_at=old_revocation)
    await database.integration_keys.insert_one(row)
    await revoke_for_guild(GUILD, OWNER)
    stored = await database.integration_keys.find_one({"_id": row["_id"]})
    assert stored["revoked_at"] == old_revocation
    assert stored["active"] is False


async def test_raw_revocation_survives_failing_character_update(database):
    """A downstream character error cannot prevent departure revocation."""
    row = key()
    await database.integration_keys.insert_one(row)
    member = MagicMock(id=OWNER)
    member.guild.id = GUILD
    with patch("services.char_mgr.mark_inactive", new=AsyncMock(side_effect=ValueError)):
        with pytest.raises(ValueError):
            await InconnuBot.on_member_remove(MagicMock(), member)
    await InconnuBot.on_raw_member_remove(MagicMock(), departure())
    assert (await database.integration_keys.find_one({"_id": row["_id"]}))["active"] is False


async def test_cull_applies_thirty_day_key_retention(database):
    """Culling removes old inactive records while preserving live and recent keys."""
    cull = import_module("tasks.cull")
    old = NOW - timedelta(days=31)
    recent = NOW - timedelta(days=29)
    removed_guild = GUILD + 1
    await database.guilds.insert_one({"guild": removed_guild, "active": False, "left": old})
    deleted = [
        key(expires_at=old),
        key(active=False, revoked_at=old),
        key(guild=removed_guild),
    ]
    retained = [
        key(),
        key(expires_at=NOW + timedelta(days=1)),
        key(expires_at=recent),
        key(active=False, revoked_at=recent),
        key(active=False, revoked_at=NOW - timedelta(days=30)),
    ]
    await database.integration_keys.insert_many([*deleted, *retained])
    empty_characters = MagicMock()
    empty_characters.__aiter__.return_value = []
    with (
        patch.object(cull, "datetime") as clock,
        patch.object(VChar, "find", return_value=empty_characters),
    ):
        clock.now.return_value = NOW
        await cull.cull()
    survivors = await database.integration_keys.find({}).to_list(None)
    assert {row["_id"] for row in survivors} == {row["_id"] for row in retained}
    assert await database.guilds.count_documents({"guild": removed_guild}) == 0


async def test_cached_departure_does_not_duplicate_revocation(database):
    """The cached event only handles characters while the raw event revokes once."""
    row = key()
    await database.integration_keys.insert_one(row)
    member = MagicMock(spec=discord.Member, id=OWNER)
    member.guild.id = GUILD
    with (
        patch("services.char_mgr.mark_inactive", new=AsyncMock()) as inactive,
        patch(
            "services.integration_lifecycle.revoke_for_guild", new=AsyncMock(wraps=revoke_for_guild)
        ) as revoke,
    ):
        await InconnuBot.on_member_remove(MagicMock(), member)
        await InconnuBot.on_raw_member_remove(MagicMock(), departure(member))
    inactive.assert_awaited_once_with(member)
    revoke.assert_awaited_once_with(GUILD, OWNER)
    assert (await database.integration_keys.find_one({"_id": row["_id"]}))["active"] is False
