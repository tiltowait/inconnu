"""Specialties UI test. (Everything but Discord stuff.)"""

from contextlib import nullcontext as does_not_raise

import pytest

import errors
from inconnu.specialties.add_remove import (
    Category,
    add_specialties,
    remove_specialties,
    validate_tokens,
)
from inconnu.specialties.tokenize import tokenize
from models.vchar import VChar
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
        ("brawl=kindred; occult=bahari", [("brawl", ["kindred"]), ("occult", ["bahari"])]),
        (
            "brawl=kindred,kine;occult=bahari;",
            [("brawl", ["kindred", "kine"]), ("occult", ["bahari"])],
        ),
        ("brawl = kindred,", [("brawl", ["kindred"])]),
        ("brawl = kindred, kine", [("brawl", ["kindred", "kine"])]),
        ("animal_ken=squirrels", [("animal_ken", ["squirrels"])]),
        # Multiword traits and specialties
        ("animal ken=big cats", [("animal ken", ["big cats"])]),
        (
            "animal   ken = big  cats , dogs; brawl=kindred hunters",
            [("animal ken", ["big cats", "dogs"]), ("brawl", ["kindred hunters"])],
        ),
        # Apostrophes, and curly ones from phones
        ("beast's fang=o'brien, dogs'", [("beast's fang", ["o'brien", "dogs'"])]),
        ("beast\u2019s fang=o\u2019brien", [("beast's fang", ["o'brien"])]),
    ],
)
def test_valid_syntax(syntax: str, expected: list[tuple[str, list[str]]]):
    tokens = tokenize(syntax)
    assert len(tokens) == len(expected)

    for received, exp in zip(tokens, expected):
        r_trait, r_specs = received
        e_trait, e_specs = exp

        assert r_trait == e_trait
        assert r_specs == e_specs


@pytest.mark.parametrize(
    "syntax",
    [
        "",  # Nothing given
        " ; ",
        "b",  # No specialty given
        "b=",
        "b=,",
        "9=kindred",  # Invalid characters
        "brawl=kindred-kine",
        "brawl=kindred, ravenous hunger",  # Hunger after the first word
    ],
)
def test_invalid_syntax(syntax: str):
    with pytest.raises(SyntaxError):
        _ = tokenize(syntax)


@pytest.mark.parametrize(
    "syntax",
    [
        "brawl=kindred occult=bahari",  # Missing ;
        "brawl=kindred, occult=bahari",  # A comma in place of ;
        "Brawl=Kindred=Kine",  # Extra =
        "brawl=big cats=dogs",  # Extra =, after a multiword specialty
        "brawl=kindred=kine occult=bahari",  # Both
    ],
)
def test_extra_equals(syntax: str):
    """A second = may be a missing ; or an extra =, which look alike, so the
    message covers both."""
    with pytest.raises(
        SyntaxError, match="Each trait takes one `=`, and traits are separated by `;`"
    ):
        _ = tokenize(syntax)


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("brawl=Kindred", [("Brawl", ["Kindred"], ["Kindred"])]),
        ("brawl=Kindred,Kine", [("Brawl", ["Kindred", "Kine"], ["Kindred", "Kine"])]),
        (
            "brawl=Kindred; craft=Knives",
            [("Brawl", ["Kindred"], ["Kindred"]), ("Craft", ["Knives"], ["Knives"])],
        ),
    ],
)
def test_add_specialties(syntax: str, expected: list, character: VChar):
    traits = add_specialties(character, syntax, Category.SPECIALTY)
    assert len(traits) == len(expected)

    for (trait, delta), exp in zip(traits, expected):
        e_trait, e_specs, e_delta = exp
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
        "Brawl=Kindred; Performance=Piano",  # One valid, one invalid
    ],
)
def test_fail_add_specialties(syntax: str, character: VChar):
    with pytest.raises(errors.TraitError):
        _ = add_specialties(character, syntax, Category.SPECIALTY)


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("Brawl=Kindred", [("Brawl", ["Kine"], ["Kindred"])]),
        ("Brawl=Kindred,Kine", [("Brawl", [], ["Kindred", "Kine"])]),
        (
            "Brawl=Kindred; Craft=Knives",
            [("Brawl", ["Kine"], ["Kindred"]), ("Craft", [], ["Knives"])],
        ),
    ],
)
def test_remove_specialties(syntax: str, expected: list, specced: VChar):
    traits = remove_specialties(specced, syntax)
    assert len(traits) == len(expected)

    for (trait, delta), exp in zip(traits, expected):
        e_trait, e_specs, e_delta = exp

        assert trait.name == e_trait
        assert trait.specialties == e_specs
        assert delta == e_delta


def test_multiword_specialties(character: VChar):
    """Multiword specialties are added to multiword traits and removed."""
    character.assign_traits({"Animal Ken": 2})
    traits = add_specialties(character, "animal ken=Big Cats, Dogs", Category.SPECIALTY)
    trait, delta = traits[0]
    assert trait.name == "Animal Ken"
    assert trait.specialties == ["Big Cats", "Dogs"]
    assert delta == ["Big Cats", "Dogs"]

    trait, delta = remove_specialties(character, "animal ken=big cats")[0]
    assert trait.specialties == ["Dogs"]
    assert delta == ["Big Cats"]


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
        (pytest.raises(errors.TraitError), "Brawl", ["Brawl"]),
        (pytest.raises(errors.TraitError), "Brawl", ["Kindred", "Brawl"]),
        (pytest.raises(errors.TraitError), "NotASkill", ["ShouldFail"]),
        (pytest.raises(errors.TraitError), "BRAWL", ["brawl"]),  # Test case-insensitivity
    ],
)
def test_validate_tokens(exception, skill: str, specs: list[str], character: VChar):
    with exception:
        validate_tokens(character, [(skill, specs)])
