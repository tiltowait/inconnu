"""Tests for constants.py."""

from constants import ATTRIBUTES_AND_SKILLS, MENTAL_SOCIAL_TRAITS, PHYSICAL_TRAITS


def test_trait_categories_partition_attributes_and_skills():
    """Every Attribute and Skill is either physical or mental/social, never both."""
    assert PHYSICAL_TRAITS.isdisjoint(MENTAL_SOCIAL_TRAITS)
    assert PHYSICAL_TRAITS | MENTAL_SOCIAL_TRAITS == ATTRIBUTES_AND_SKILLS
