"""Character traits tests."""

import pytest

import errors
import tests.characters
from constants import ATTRIBUTES, DISCIPLINES, SKILLS, UNIVERSAL_TRAITS
from models import VChar
from models.vchardocs import VCharTrait


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
    sorted_traits = sorted(custom_traits.items(), key=lambda t: t[0].casefold())

    # Test against the list
    for trait, (expected_name, expected_rating) in zip(empty_vampire.traits, sorted_traits):
        assert trait.type == category.value
        assert trait.name == expected_name
        assert trait.rating == expected_rating


def test_find_trait(vampire: VChar, custom_traits: dict[str, int]):
    for trait, rating in custom_traits.items():
        found = vampire.find_trait(trait)
        assert found.name == trait
        assert found.rating == rating

    with pytest.raises(errors.TraitNotFound):
        _ = vampire.find_trait("fake")


def test_ambiguous_trait(vampire: VChar):
    trait = vampire.traits[0].name
    vampire.assign_traits({f"{trait}{trait}": 5})
    with pytest.raises(errors.AmbiguousTraitError):
        _ = vampire.find_trait(trait[0])


def test_find_exact_trait(vampire: VChar):
    trait = vampire.traits[0]
    found = vampire.find_trait(trait.name, True)

    assert trait.name == found.name
    assert trait.rating == found.rating
    assert found.exact

    with pytest.raises(errors.TraitNotFound):
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
    with pytest.raises(errors.TraitNotFound):
        _ = vampire.find_trait(trait.name)

    # Hard check of traits
    for extant in vampire.traits:
        assert trait.name != extant.name


def test_has_trait(vampire: VChar):
    trait = vampire.traits[0]
    assert vampire.has_trait(trait.name)


@pytest.mark.parametrize("trait", UNIVERSAL_TRAITS)
def test_universal_fail(trait: str, vampire: VChar):
    """Test that we can't add universal traits."""
    with pytest.raises(ValueError):
        vampire.assign_traits({trait: 1})


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

    with pytest.raises(errors.TraitNotFound):
        vampire.add_specialties("FakeSkill", ["FakeTrait"])

    with pytest.raises(errors.SpecialtiesNotAllowed):
        vampire.assign_traits({"Strength": 1}, VCharTrait.Type.ATTRIBUTE)
        vampire.add_specialties("Strength", ["ShouldNotWork"])


def test_add_disciplines(vampire: VChar):
    vampire.assign_traits({"Auspex": 3}, VCharTrait.Type.DISCIPLINE)

    for trait in vampire.traits:
        if trait.name == "Auspex":
            assert trait.is_discipline
            break

    vampire.add_powers("Auspex", ["Premonition"])
    with pytest.raises(errors.SpecialtiesNotAllowed):
        vampire.add_powers("one", "kindred")


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_attribute_adding(attribute: str, empty_vampire: VChar):
    empty_vampire.assign_traits({attribute: 1})
    trait = empty_vampire.find_trait(attribute)
    assert trait.type == VCharTrait.Type.ATTRIBUTE
    assert empty_vampire.traits[0].is_attribute

    with pytest.raises(errors.SpecialtiesNotAllowed):
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

    trait = empty_vampire.raw_traits[0]  # This doesn't create a copy
    assert trait.specialties == ["Kindred", "StreetFighting"]

    empty_vampire.remove_specialties("Brawl", "Kindred")
    assert trait.specialties == ["StreetFighting"]

    empty_vampire.remove_specialties("Brawl", "StreetFighting")
    assert not trait.has_specialties


def test_specialty_find(vampire: VChar):
    vampire.assign_traits({"Brawl": 1})
    vampire.add_specialties("Brawl", "Kindred")
    trait = vampire.find_trait(".k")

    assert trait.name == "Brawl (Kindred)"
    assert trait.rating == 2
    assert trait.type == VCharTrait.Type.SKILL


def test_exact_trait_find(vampire: VChar):
    vampire.assign_traits({"Brawl": 1})
    trait = vampire.find_trait("brawl", True)
    assert trait.name == "Brawl"

    with pytest.raises(errors.TraitNotFound):
        _ = vampire.find_trait("b", True)


def test_trait_binsort(empty_vampire: VChar):
    empty_vampire.assign_traits({"B": 2, "C": 3})
    empty_vampire.assign_traits({"A": 1})

    assert empty_vampire.traits[0].name == "A"
    assert empty_vampire.traits[1].name == "B"
    assert empty_vampire.traits[2].name == "C"


@pytest.mark.parametrize("discipline", DISCIPLINES)
def test_discipline_fallback(discipline: str, empty_vampire: VChar):
    empty_vampire.assign_traits({discipline: 1})
    assert empty_vampire.traits[0].is_discipline


def test_traits_copied(vampire: VChar):
    expected_name = vampire.traits[0].name
    vampire.traits[0].name = "Fakeo"
    assert vampire.traits[0].name == expected_name


def test_update_trait(vampire: VChar):
    trait = vampire.traits[0].name
    rating = vampire.traits[0].rating
    assert rating != 5

    vampire.assign_traits({trait: 5})
    assert vampire.traits[0].rating == 5
    assert vampire.find_trait(trait).rating == 5
