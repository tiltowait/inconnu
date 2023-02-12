"""Character traits tests."""

import pytest

import inconnu.errors
import tests.characters
from inconnu.constants import ATTRIBUTES, SKILLS, UNIVERSAL_TRAITS
from inconnu.models import VChar
from inconnu.models.vchardocs import VCharTrait


@pytest.fixture
def empty_vampire() -> VChar:
    """A dummy vampire with no traits."""
    return tests.characters.gen_char("vampire")


@pytest.fixture
def custom_traits() -> dict[str, int]:
    return {"one": 1, "two": 2, "three": 3}


@pytest.fixture
def vampire(custom_traits) -> VChar:
    """A dummy vampire with some custom traits."""
    vamp = tests.characters.gen_char("vampire")
    vamp.assign_traits(custom_traits)
    return vamp


@pytest.mark.parametrize("category", list(VCharTrait.Type))
def test_add_traits(category: str, empty_vampire: VChar, custom_traits: dict[str, int]):
    """Add traits of different categories and test their values."""
    empty_vampire.assign_traits(custom_traits, category)

    # Test against the list
    for trait, (expected_name, expected_rating) in zip(empty_vampire.traits, custom_traits.items()):
        assert trait.type == category.value
        assert trait.name == expected_name
        assert trait.rating == expected_rating


def test_find_trait(vampire: VChar, custom_traits: dict[str, int]):
    for trait, rating in custom_traits.items():
        found = vampire.find_trait(trait)
        assert found.name == trait
        assert found.rating == rating

    with pytest.raises(inconnu.errors.TraitNotFound):
        _ = vampire.find_trait("fake")


def test_ambiguous_trait(vampire: VChar):
    trait = vampire.traits[0].name
    vampire.assign_traits({f"{trait}{trait}": 5})
    with pytest.raises(inconnu.errors.AmbiguousTraitError):
        _ = vampire.find_trait(trait[0])


def test_find_exact_trait(vampire: VChar):
    trait = vampire.traits[0]
    found = vampire.find_trait(trait.name, True)

    assert trait.name == found.name
    assert trait.rating == found.rating
    assert found.exact

    with pytest.raises(inconnu.errors.TraitNotFound):
        _ = vampire.find_trait(trait.name[0], True)


def test_delete_trait(vampire: VChar):
    trait = vampire.traits[0]
    found = vampire.find_trait(trait.name)
    assert trait.name == found.name
    assert trait.rating == found.rating
    assert found.exact

    trait_count = len(vampire.traits)

    vampire.delete_trait(trait.name)
    assert len(vampire.traits) == trait_count - 1
    with pytest.raises(inconnu.errors.TraitNotFound):
        _ = vampire.find_trait(trait.name)

    # Hard check of traits
    for extant in vampire.traits:
        assert trait.name != extant.name


def test_has_trait(vampire: VChar):
    trait = vampire.traits[0]
    assert vampire.has_trait(trait.name)


def test_universal_fail(vampire: VChar):
    """Test that we can't add universal traits."""
    for universal in UNIVERSAL_TRAITS:
        with pytest.raises(ValueError):
            vampire.assign_traits({universal: 1})


def test_add_specialties(vampire: VChar):
    vampire.assign_traits({"Brawl": 3}, VCharTrait.Type.SKILL)
    vampire.add_specialties("Brawl", ["Kindred", "StreetFighting"])

    for trait in vampire.traits:
        if trait.name == "Brawl":
            assert not trait.is_attribute
            assert not trait.is_custom
            assert not trait.is_discipline
            assert not trait.is_inherent
            assert trait.is_skill

            assert len(trait.specialties) == 2
            assert "Kindred" in trait.specialties
            assert "StreetFighting" in trait.specialties
            break

    with pytest.raises(inconnu.errors.TraitNotFound):
        vampire.add_specialties("FakeSkill", ["FakeTrait"])

    with pytest.raises(inconnu.errors.SpecialtiesNotAllowed):
        vampire.assign_traits({"Strength": 1}, VCharTrait.Type.ATTRIBUTE)
        vampire.add_specialties("Strength", ["ShouldNotWork"])


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_attribute_adding(attribute: str, empty_vampire: VChar):
    empty_vampire.assign_traits({attribute: 1})
    trait = empty_vampire.find_trait(attribute)
    assert trait.type == VCharTrait.Type.ATTRIBUTE
    assert empty_vampire.traits[0].is_attribute

    with pytest.raises(inconnu.errors.SpecialtiesNotAllowed):
        empty_vampire.add_specialties(attribute, ["One"])
    assert not empty_vampire.traits[0].has_specialties


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_adding(skill: str, empty_vampire: VChar):
    empty_vampire.assign_traits({skill: 1})
    trait = empty_vampire.find_trait(skill)
    assert trait.type == VCharTrait.Type.SKILL
    assert empty_vampire.traits[0].is_skill

    empty_vampire.add_specialties(skill, ["One"])
    assert empty_vampire.traits[0].has_specialties


def test_remove_traits(empty_vampire: VChar):
    empty_vampire.assign_traits({"Brawl": 3})
    empty_vampire.add_specialties("Brawl", ["Kindred", "StreetFighting"])

    trait = empty_vampire._traits[0]  # This doesn't create a copy
    assert trait.specialties == ["Kindred", "StreetFighting"]

    empty_vampire.remove_specialties("Brawl", "Kindred")
    assert trait.specialties == ["StreetFighting"]

    empty_vampire.remove_specialties("Brawl", "StreetFighting")
    assert not trait.has_specialties


def test_specialty_find(vampire: VChar):
    vampire.assign_traits({"Brawl": 1})
    vampire.add_specialties("Brawl", "Kindred")
    trait = vampire.find_trait(":k")

    assert trait.name == "Brawl (Kindred)"
    assert trait.rating == 2
    assert trait.type == VCharTrait.Type.SKILL


def test_exact_trait_find(vampire: VChar):
    vampire.assign_traits({"Brawl": 1})
    trait = vampire.find_trait("brawl", True)
    assert trait.name == "Brawl"

    with pytest.raises(inconnu.errors.TraitNotFound):
        _ = vampire.find_trait("b", True)
