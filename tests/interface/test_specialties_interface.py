"""Specialties UI test. (Everything but Discord stuff.)"""

from contextlib import nullcontext as does_not_raise

import pytest

import inconnu.errors
from inconnu.models.vchar import VChar
from inconnu.specialties.add_remove import (
    Category,
    add_specialties,
    remove_specialties,
    validate_tokens,
)
from inconnu.specialties.tokenize import tokenize
from tests.characters import gen_char


@pytest.fixture
def character() -> VChar:
    char = gen_char("vampire")
    char.assign_traits({"Brawl": 1, "Craft": 2, "Oblivion": 3})
    return char


@pytest.fixture
def specced(character: VChar) -> VChar:
    character.add_specialties("Brawl", ["Kindred", "Kine"])
    character.add_specialties("Craft", ["Knives"])
    return character


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("brawl=kindred", [("brawl", ["kindred"])]),
        ("brawl=kindred,kine", [("brawl", ["kindred", "kine"])]),
        ("brawl=kindred occult=bahari", [("brawl", ["kindred"]), ("occult", ["bahari"])]),
        (
            "brawl=kindred,kine occult=bahari",
            [("brawl", ["kindred", "kine"]), ("occult", ["bahari"])],
        ),
        ("brawl = kindred,", [("brawl", ["kindred"])]),
        ("brawl = kindred, kine", [("brawl", ["kindred", "kine"])]),
        ("animal_ken=squirrels", [("animal_ken", ["squirrels"])]),
    ],
)
def test_valid_syntax(syntax: str, expected: list[tuple[str, list[str]]]):
    tokens = tokenize(syntax)
    assert len(tokens) == len(expected)

    for received, expected in zip(tokens, expected):
        r_trait, r_specs = received
        e_trait, e_specs = expected

        assert r_trait == e_trait
        assert r_specs == e_specs


@pytest.mark.parametrize(
    "syntax",
    [
        "b",  # No specialty given
        "9",  # Invalid character
        "brawl=kindred=kine,test",  # Multi equals
        "brawl=kindred, kine=test",
    ],
)
def test_invalid_syntax(syntax: str):
    with pytest.raises(SyntaxError):
        _ = tokenize(syntax)


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("brawl=Kindred", [("Brawl", ["Kindred"], ["Kindred"])]),
        ("brawl=Kindred,Kine", [("Brawl", ["Kindred", "Kine"], ["Kindred", "Kine"])]),
        (
            "brawl=Kindred craft=Knives",
            [("Brawl", ["Kindred"], ["Kindred"]), ("Craft", ["Knives"], ["Knives"])],
        ),
    ],
)
def test_add_specialties(syntax: str, expected: list, character: VChar):
    traits = add_specialties(character, syntax, Category.SPECIALTY)
    assert len(traits) == len(expected)

    for trait, expected in zip(traits, expected):
        trait, delta = trait
        e_trait, e_specs, e_delta = expected
        assert trait.name == e_trait
        assert trait.specialties == e_specs
        assert delta == e_delta


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("brawl=Kindred,Kine", ["Kine"]),
        ("brawl=Kindred,Werewolves,Kine", ["Kine", "Werewolves"]),
    ],
)
def test_add_specialties_intersection(syntax: str, expected: list[str], character: VChar):
    """Ensure that the delta filters out duplicates."""
    character.add_specialties("Brawl", "Kindred")

    _, delta = add_specialties(character, syntax, Category.SPECIALTY)[0]
    assert delta == expected


@pytest.mark.parametrize(
    "syntax",
    [
        "Performance=Piano",  # Only invalid
        "Brawl=Kindred Performance=Piano",  # One valid, one invalid
    ],
)
def test_fail_add_specialties(syntax: str, character: VChar):
    with pytest.raises(inconnu.errors.TraitError):
        _ = add_specialties(character, syntax, Category.SPECIALTY)


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("Brawl=Kindred", [("Brawl", ["Kine"], ["Kindred"])]),
        ("Brawl=Kindred,Kine", [("Brawl", [], ["Kindred", "Kine"])]),
        (
            "Brawl=Kindred Craft=Knives",
            [("Brawl", ["Kine"], ["Kindred"]), ("Craft", [], ["Knives"])],
        ),
    ],
)
def test_remove_specialties(syntax: str, expected: list, specced: VChar):
    traits = remove_specialties(specced, syntax)
    assert len(traits) == len(expected)

    for trait, expected in zip(traits, expected):
        trait, delta = trait
        e_trait, e_specs, e_delta = expected

        assert trait.name == e_trait
        assert trait.specialties == e_specs
        assert delta == e_delta


def test_add_powers(character: VChar):
    powers = add_specialties(character, "oblivion=NecroticPlague", Category.POWER)
    assert len(powers) == 1
    _, delta = powers[0]

    assert delta == ["NecroticPlague"]


@pytest.mark.parametrize(
    "exception,skill,specs",
    [
        (does_not_raise(), "Brawl", ["Kindred"]),
        (does_not_raise(), "Brawl", ["Kindred", "Kine"]),
        (pytest.raises(inconnu.errors.TraitError), "Brawl", ["Brawl"]),
        (pytest.raises(inconnu.errors.TraitError), "Brawl", ["Kindred", "Brawl"]),
        (pytest.raises(inconnu.errors.TraitError), "NotASkill", ["ShouldFail"]),
        (pytest.raises(inconnu.errors.TraitError), "BRAWL", ["brawl"]),  # Test case-insensitivity
    ],
)
def test_validate_tokens(exception, skill: str, specs: list[str], character: VChar):
    with exception:
        validate_tokens(character, [(skill, specs)])
