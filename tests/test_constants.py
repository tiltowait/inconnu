"""Tests for constants.py."""

import pytest

from constants import (
    ATTRIBUTES_AND_SKILLS,
    MENTAL_SOCIAL_TRAITS,
    PHYSICAL_TRAITS,
    Impairment,
    RollCategory,
)


def test_trait_categories_partition_attributes_and_skills():
    """Every Attribute and Skill is either physical or mental/social, never both."""
    assert PHYSICAL_TRAITS.isdisjoint(MENTAL_SOCIAL_TRAITS)
    assert PHYSICAL_TRAITS | MENTAL_SOCIAL_TRAITS == ATTRIBUTES_AND_SKILLS


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
        (Impairment.TOTAL, [NONE, PHYSICAL, MENTAL, MIXED]),
    ],
)
@pytest.mark.parametrize("category", [NONE, PHYSICAL, MENTAL, MIXED])
def test_impairment_penalizes(
    impairment: Impairment, penalized: list[RollCategory], category: RollCategory
):
    """Impairment penalizes rolls with an impaired category. Total impairment
    penalizes every roll, including those with no category."""
    assert impairment.penalizes(category) is (category in penalized)
