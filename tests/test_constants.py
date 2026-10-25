"""Tests for constants.py."""

from constants import ATTRIBUTES, MENTAL_SOCIAL_ATTRIBUTES, PHYSICAL_ATTRIBUTES


def test_attribute_categories_partition_attributes():
    """Every Attribute is either physical or mental/social, never both."""
    assert PHYSICAL_ATTRIBUTES.isdisjoint(MENTAL_SOCIAL_ATTRIBUTES)
    assert PHYSICAL_ATTRIBUTES | MENTAL_SOCIAL_ATTRIBUTES == ATTRIBUTES
