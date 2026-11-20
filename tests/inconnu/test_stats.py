"""Tests for inconnu/stats.py."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId
from mongomock_motor import AsyncMongoMockClient
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

import db
import inconnu
from inconnu.stats import (
    _gen_roll,
    _rename_pool_trait,
    guild_joined,
    guild_left,
    log_roll,
    trait_renamed,
)
from models import Impairment, VGuild

type MockCollection = AsyncMock


@pytest.fixture
def rolls() -> Generator[MockCollection]:
    """The rolls collection."""
    collection = AsyncMock(spec=AsyncCollection)
    with patch.object(db, "rolls", collection):
        yield collection


@pytest.mark.parametrize(
    "penalty,impaired",
    [
        (Impairment.NONE, False),
        (Impairment.PHYSICAL, True),
        (Impairment.MENTAL, True),
        (Impairment.TOTAL, True),
    ],
)
def test_roll_entry_records_impairment(penalty: Impairment, impaired: bool):
    """Roll entries record whether an Impairment penalty was applied."""
    roll = inconnu.Roll(5, 0, 0, pool_str="Strength + Brawl", impairment_penalty=penalty)
    entry = _gen_roll(1, 2, 3, 4, None, roll, None)

    assert entry["impaired"] is impaired


@pytest.mark.parametrize("hidden", [False, True])
def test_roll_entry_records_hidden(hidden: bool):
    """Roll entries record whether the dice were hidden."""
    roll = inconnu.Roll(5, 0, 0)
    entry = _gen_roll(1, 2, 3, 4, None, roll, None, hidden=hidden)

    assert entry["hidden"] is hidden


async def test_first_log_inserts(rolls: MockCollection):
    """A roll's first log inserts its entry without looking for one."""
    roll = inconnu.Roll(5, 0, 0)
    await log_roll(1, 2, 3, 4, None, roll, None)

    rolls.insert_one.assert_awaited_once()
    assert rolls.insert_one.await_args.args[0]["_id"] == roll.id
    rolls.find_one.assert_not_awaited()
    rolls.update_one.assert_not_awaited()


async def test_reroll_updates(rolls: MockCollection):
    """A reroll updates its roll's entry without looking for it."""
    roll = inconnu.Roll(5, 0, 0)
    roll.reroll("reroll_failures")
    await log_roll(1, 2, 3, None, None, roll, None)

    rolls.update_one.assert_awaited_once()
    query, update = rolls.update_one.await_args.args
    assert query == {"_id": roll.id}
    assert update["$set"]["reroll"]["strategy"] == "failures"
    rolls.find_one.assert_not_awaited()
    rolls.insert_one.assert_not_awaited()


async def test_rejoin_after_cull_recreates_guild():
    """A guild culled after the bot left is created again when it returns."""
    guild = MagicMock(spec=discord.Guild, id=2718281828)
    guild.name = "Returning Guild"
    VGuild.get_or_fetch.cache_clear()

    await guild_joined(guild)
    await guild_left(guild)
    await VGuild.find({"guild": guild.id}).delete()  # Culled
    await guild_joined(guild)

    vguild = await VGuild.find_one({"guild": guild.id})
    assert vguild is not None
    assert vguild.active is True
    await vguild.delete()


@pytest.mark.parametrize(
    "pool,expected",
    [
        ("Night Driving", "Getaway Driving"),
        (
            "Strength + Night Driving (Rain, Snow) - 1",
            "Strength + Getaway Driving (Rain, Snow) - 1",
        ),
        ("-night driving + Wits", "-Getaway Driving + Wits"),
        ("Wits - Night Driving", "Wits - Getaway Driving"),
        # Only whole trait names
        ("Night Driving Expert + Night", "Night Driving Expert + Night"),
        ("Drive (Night Driving)", "Drive (Night Driving)"),
    ],
)
def test_rename_pool_trait(pool: str, expected: str):
    """A renamed trait is replaced wherever it's a whole operand's trait."""
    assert _rename_pool_trait(pool, "Night Driving", "Getaway Driving") == expected


async def test_trait_renamed():
    """Only the character's rolls using the trait are rewritten."""
    charid, other = PydanticObjectId(), PydanticObjectId()
    collection = AsyncMongoMockClient().db.rolls
    await collection.insert_many(
        [
            {"charid": charid, "pool": "Wits + Night Driving"},
            {"charid": charid, "pool": "Strength + Brawl"},
            {"charid": charid, "pool": "Night Driving Expert"},
            {"charid": charid, "pool": None},
            {"charid": other, "pool": "Wits + Night Driving"},
        ]
    )

    async def bulk_write(updates: list[UpdateOne], ordered=True):
        """Apply the updates; mongomock's bulk_write rejects pymongo's."""
        for update in updates:
            await collection.update_one(update._filter, update._doc)

    with (
        patch.object(db, "rolls", collection),
        patch.object(collection, "bulk_write", bulk_write),
    ):
        assert await trait_renamed(charid, "night driving", "Getaway Driving") == 1

    docs = [doc async for doc in collection.find()]
    pools = sorted([doc["charid"] == charid, doc["pool"] or ""] for doc in docs)
    assert pools == [
        [False, "Wits + Night Driving"],
        [True, ""],
        [True, "Night Driving Expert"],
        [True, "Strength + Brawl"],
        [True, "Wits + Getaway Driving"],
    ]
