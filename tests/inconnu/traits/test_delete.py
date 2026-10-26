"""Tests for traits/delete.py."""

import tests.characters
from inconnu.traits.delete import __delete_traits as delete_traits


def test_delete_multiple_core_traits():
    """Every core Trait in a multi-Trait deletion is set to 0, not removed."""
    char = tests.characters.gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 2, "Custom": 1, "Wits": 4})

    outcome = delete_traits(char, "Custom", "Strength", "Brawl", "Wits")

    assert outcome.errors == []
    assert char.find_trait("Strength").rating == 0
    assert char.find_trait("Brawl").rating == 0
    assert char.find_trait("Wits").rating == 0
    assert all(trait.name != "Custom" for trait in char.traits)
