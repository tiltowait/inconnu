"""Tests for models/impairment.py."""

import pytest

from models import Impairment, ImpairmentCategory, RollCategory


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
        ("Strength + Intimidation", RollCategory.PHYSICAL),
        ("Composure + Firearms", RollCategory.MENTAL),
        ("Intelligence + Brawl", RollCategory.MENTAL),
        ("Strength + Wits", RollCategory.MIXED),
        ("Brawl + 2", RollCategory.NONE),
        ("Potence", RollCategory.NONE),
    ],
)
def test_roll_category_from_pool(pool: str | None, expected: RollCategory):
    """A pool's category comes from its Attributes. Skills are ignored."""
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


@pytest.mark.parametrize(
    "choice,category",
    [
        (ImpairmentCategory.IGNORE, RollCategory.NONE),
        (ImpairmentCategory.PHYSICAL, RollCategory.PHYSICAL),
        (ImpairmentCategory.MENTAL, RollCategory.MENTAL),
    ],
)
def test_impairment_category_roll_category(choice: ImpairmentCategory, category: RollCategory):
    """Each choice stands for a roll category; Ignore stands for none, which no
    Impairment penalizes."""
    assert choice.roll_category == category
    assert not Impairment.TOTAL.penalizes(ImpairmentCategory.IGNORE.roll_category)


@pytest.mark.parametrize(
    "value,expected",
    [(None, None), ("ignore", ImpairmentCategory.IGNORE), ("mental", ImpairmentCategory.MENTAL)],
)
def test_impairment_category_from_option(value: str | None, expected: ImpairmentCategory | None):
    """Command option values become choices; no value means no choice."""
    assert ImpairmentCategory.from_option(value) == expected
