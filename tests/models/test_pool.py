"""Tests for models/pool.py."""

import pytest

from models.pool import PoolOperand, join_pool, pool_traits, split_pool


@pytest.mark.parametrize(
    "pool,expected",
    [
        ("Strength", {"Strength"}),
        ("Strength + Brawl", {"Strength", "Brawl"}),
        ("Strength + Animal Ken (Big Cats, Dogs) - 1", {"Strength", "Animal Ken", "1"}),
        ("-Strength + Beast's Fang", {"Strength", "Beast's Fang"}),
        ("Wits - Night Driving", {"Wits", "Night Driving"}),
    ],
)
def test_pool_traits(pool: str, expected: set[str]):
    """Pools split on their operators, without specialties or minus signs."""
    assert pool_traits(pool) == expected


def test_split_pool():
    """Pools split into operands, with their signs and specialties, and the
    operators between them."""
    assert split_pool("-Strength + Animal Ken (Big Cats, Dogs) - 1") == [
        PoolOperand("-", "Strength", None),
        " + ",
        PoolOperand("", "Animal Ken", "Big Cats, Dogs"),
        " - ",
        PoolOperand("", "1", None),
    ]


@pytest.mark.parametrize(
    "pool",
    [
        "Strength",
        "Wits + Awareness",
        "-Strength + Animal Ken (Big Cats, Dogs) - 1",
        "Oblivion (Where the Shroud Thins) + Power Bonus",
        "Beast's Fang - 2",
    ],
)
def test_join_pool_reverses_split(pool: str):
    """Splitting and rejoining gives back the same pool."""
    assert join_pool(split_pool(pool)) == pool
