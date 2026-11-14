"""Tests for inconnu/stats.py."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pymongo.asynchronous.collection import AsyncCollection

import db
import inconnu
from inconnu.stats import _gen_roll, log_roll
from models import Impairment

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
