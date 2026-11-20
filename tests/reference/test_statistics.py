"""Tests for inconnu/reference/statistics.py."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import mongomock
import pytest
from beanie import PydanticObjectId

from inconnu.reference.statistics import trait_successes_pipeline

type MockCollection = mongomock.Collection

CHARID = PydanticObjectId()
SINCE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def rolls() -> Iterator[MockCollection]:
    """An in-memory rolls collection."""
    yield mongomock.MongoClient().db.rolls


def add_roll(
    rolls: MockCollection,
    pool: str | None,
    margin: int,
    difficulty: int,
    *,
    reroll_margin: int | None = None,
    charid: PydanticObjectId = CHARID,
    date: datetime = SINCE,
    use_in_stats=True,
):
    """Insert a roll. Its successes are its margin (or reroll margin) plus its
    difficulty."""
    rolls.insert_one(
        {
            "charid": charid,
            "pool": pool,
            "margin": margin,
            "difficulty": difficulty,
            "reroll": None if reroll_margin is None else {"margin": reroll_margin},
            "date": date,
            "use_in_stats": use_in_stats,
        }
    )


def successes(rolls: MockCollection) -> dict[str, int]:
    """Run the pipeline, returning each operand's total successes."""
    docs = rolls.aggregate(trait_successes_pipeline(CHARID, SINCE))
    return {doc["_id"]: doc["successes"] for doc in docs}


def test_multiword_traits_and_specialties(rolls: MockCollection):
    """Multiword traits count under their full names, without specialties."""
    add_roll(rolls, "Strength + Brawl (Kindred) - 1", 1, 2)
    add_roll(rolls, "Wits + Animal Ken (Big Cats, Dogs)", 0, 3)
    add_roll(rolls, "Animal Ken + Beast's Fang", 2, 1, reroll_margin=4)

    assert successes(rolls) == {
        "Strength": 3,
        "Brawl": 3,
        "Wits": 3,
        "Animal Ken": 8,  # 3 + (4 + 1): the reroll's margin replaces the original
        "Beast's Fang": 5,
    }


def test_subtracted_traits_not_counted(rolls: MockCollection):
    """Subtracted traits aren't counted, wherever they are in the pool."""
    add_roll(rolls, "-Strength + Animal Ken", 1, 1)
    add_roll(rolls, "Wits - Animal Ken - Brawl (Kindred) + Resolve", 1, 1)

    assert successes(rolls) == {"-Strength": 2, "Animal Ken": 2, "Wits": 2, "Resolve": 2}


def test_filtered_rolls(rolls: MockCollection):
    """Only the character's counted, pooled rolls since the date are included."""
    add_roll(rolls, "Wits", 1, 1)
    add_roll(rolls, "Wits", 1, 1, charid=PydanticObjectId())
    add_roll(rolls, "Wits", 1, 1, date=SINCE - timedelta(days=1))
    add_roll(rolls, "Wits", 1, 1, use_in_stats=False)
    add_roll(rolls, None, 1, 1)

    assert successes(rolls) == {"Wits": 2}
