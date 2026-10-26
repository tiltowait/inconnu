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


def test_delete_core_trait_clears_specialties():
    """Deleting a core Trait removes its specialties."""
    char = tests.characters.gen_char("vampire")
    char.assign_traits({"Brawl": 2, "Athletics": 3})
    char.add_specialties("Brawl", ["Grappling", "Kindred"])
    char.add_specialties("Athletics", "Climbing")

    delete_traits(char, "Brawl")

    brawl = next(trait for trait in char.traits if trait.name == "Brawl")
    athletics = next(trait for trait in char.traits if trait.name == "Athletics")
    assert brawl.rating == 0
    assert brawl.specialties == []
    assert athletics.specialties == ["Climbing"]
