"""Tests for models/impairment.py."""

import pytest

from models import Impairment, RollCategory


@pytest.mark.parametrize(
    "pool,expected",
    [
        (None, RollCategory.NONE),
        ("Strength + Brawl", RollCategory.PHYSICAL),
        ("Strength + 2", RollCategory.PHYSICAL),
        ("Brawl (Kindred) + Strength", RollCategory.PHYSICAL),
        ("Wits + Awareness", RollCategory.MENTAL),
        ("Charisma + Persuasion", RollCategory.MENTAL),
        ("Resolve + Oblivion + PowerBonus", RollCategory.MENTAL),
        ("Strength + Intimidation", RollCategory.MIXED),
        ("Potence", RollCategory.NONE),
    ],
)
def test_roll_category_from_pool(pool: str | None, expected: RollCategory):
    """A pool's category comes from its Attributes and Skills."""
    assert RollCategory.from_pool(pool) == expected


NONE, PHYSICAL, MENTAL, MIXED = (
    RollCategory.NONE,
    RollCategory.PHYSICAL,
    RollCategory.MENTAL,
    RollCategory.MIXED,
)


@pytest.mark.parametrize(
    "impairment,penalized",
    [
        (Impairment.NONE, []),
        (Impairment.PHYSICAL, [PHYSICAL, MIXED]),
        (Impairment.MENTAL, [MENTAL, MIXED]),
        (Impairment.TOTAL, [PHYSICAL, MENTAL, MIXED]),
    ],
)
@pytest.mark.parametrize("category", [NONE, PHYSICAL, MENTAL, MIXED])
def test_impairment_penalizes(
    impairment: Impairment, penalized: list[RollCategory], category: RollCategory
):
    """Impairment penalizes rolls with an impaired category. Rolls with no
    category are never penalized, even by total impairment."""
    assert impairment.penalizes(category) is (category in penalized)
