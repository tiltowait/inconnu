"""Tests for constants.py."""

import pytest

from constants import ATTRIBUTES, MENTAL_SOCIAL_ATTRIBUTES, PHYSICAL_ATTRIBUTES, core_trait


def test_attribute_categories_partition_attributes():
    """Every Attribute is either physical or mental/social, never both."""
    assert PHYSICAL_ATTRIBUTES.isdisjoint(MENTAL_SOCIAL_ATTRIBUTES)
    assert PHYSICAL_ATTRIBUTES | MENTAL_SOCIAL_ATTRIBUTES == ATTRIBUTES


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Strength", "Strength"),
        ("STRENGTH", "Strength"),
        ("Animal Ken", "Animal Ken"),
        ("animalken", "Animal Ken"),
        ("animal  ken", "Animal Ken"),
        ("anim", None),
        ("Oblivion", None),  # Disciplines aren't core
        ("Night Driving", None),
    ],
)
def test_core_trait(name: str, expected: str | None):
    """Attributes and Skills are found ignoring case and spaces."""
    assert core_trait(name) == expected
