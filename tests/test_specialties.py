"""Specialty test suite."""

import pytest

import inconnu.errors
from inconnu.models.vchardocs import VCharTrait

SPECIALTIES = ["Kindred", "StreetFighting", "Kine"]  # Shared specialties


@pytest.fixture
def skill() -> VCharTrait:
    """A basic trait."""
    return VCharTrait(name="Brawl", rating=4, type=VCharTrait.Type.SKILL.value)


def gen_skill(*specialties: str) -> VCharTrait:
    """Shorthand skill generation."""
    skill = VCharTrait(name="Brawl", rating=4, type=VCharTrait.Type.SKILL.value)
    skill.add_specialties(specialties)

    return skill


@pytest.mark.parametrize(
    "needle,exact,count,name,rating",
    [
        ("b", False, 1, "Brawl", 4),
        ("q", False, 0, None, None),
        ("b", True, 0, None, None),
        ("Brawl", True, 1, "Brawl", 4),
        ("brawl", True, 1, "Brawl", 4),
        ("BRAWL", True, 1, "Brawl", 4),
    ],
)
def test_basic_skill_matching(needle, exact, count, name, rating, skill):
    matches = skill.matching(needle, exact)
    assert len(matches) == count

    if matches:
        assert matches[0].name == name
        assert matches[0].rating == rating


def test_specialty_addition(skill: VCharTrait):
    assert len(skill.specialties) == 0

    skill.add_specialties("Kindred")
    assert len(skill.specialties) == 1

    skill.add_specialties("Kindred")
    assert len(skill.specialties) == 1, "Two 'Kindred' specs were added"

    skill.add_specialties("StreetFighting")
    assert len(skill.specialties) == 2, "'StreetFighting' wasn't added"

    skill.add_specialties(["One", "Two", "Two"])
    assert len(skill.specialties) == 4, "List wasn't added"


def test_alphabetic_specialties(skill: VCharTrait):
    skill.add_specialties(["Kine", "Kindred", "Apples"])
    skill.add_specialties("Blip")
    assert skill.specialties == ["Apples", "Blip", "Kindred", "Kine"]


def test_specialty_removal(skill: VCharTrait):
    skill.add_specialties(["One", "Two", "Three"])
    assert len(skill.specialties) == 3

    skill.remove_specialties("One")
    assert len(skill.specialties) == 2

    skill.remove_specialties("One")
    assert len(skill.specialties) == 2, "Nothing should have been removed"

    skill.remove_specialties(["Two", "Three"])
    assert len(skill.specialties) == 0, "Specialties should be gone"


@pytest.mark.parametrize(
    "needle,exact,count,expectations",
    [
        # Inexact
        (":z", False, 0, None),
        (":k:z", False, 0, None),
        ("b:kind", False, 1, [("Brawl (Kindred)", 5, False, "Brawl:Kindred")]),
        (":kind", False, 1, [("Brawl (Kindred)", 5, False, "Brawl:Kindred")]),
        ("brawl:kindred", False, 1, [("Brawl (Kindred)", 5, True, "Brawl:Kindred")]),
        (
            ":k",
            False,
            2,
            [
                ("Brawl (Kindred)", 5, False, "Brawl:Kindred"),
                ("Brawl (Kine)", 5, False, "Brawl:Kine"),
            ],
        ),
        (
            ":kind:s",
            False,
            1,
            [("Brawl (Kindred, StreetFighting)", 6, False, "Brawl:Kindred:StreetFighting")],
        ),
        # Exact
        ("Brawl", True, 1, [("Brawl", 4, True, "Brawl")]),
        ("brawl", True, 1, [("Brawl", 4, True, "Brawl")]),
        ("b", True, 0, None),
        ("brawl:kindred", True, 1, [("Brawl (Kindred)", 5, True, "Brawl:Kindred")]),
        ("brawl:kin", True, 0, None),
        (
            "Brawl:Kindred:StreetFighting",
            True,
            1,
            [("Brawl (Kindred, StreetFighting)", 6, True, "Brawl:Kindred:StreetFighting")],
        ),
        (":kindred", True, 0, None),
    ],
)
def test_specialty_matching(
    needle: str,
    exact: bool,
    count: int,
    expectations: list[tuple[str, int, bool]],
    skill: VCharTrait,
):
    skill.add_specialties(SPECIALTIES)
    assert len(skill.specialties) == 3

    matches = skill.matching(needle, exact)
    assert len(matches) == count

    if matches:
        for match, expected in zip(matches, expectations):
            name, rating, is_exact, key = expected
            assert match.name == name
            assert match.rating == rating
            assert match.exact == is_exact
            assert match.key == key


@pytest.mark.parametrize(
    "needle,exact,count,expectations",
    [
        # Inexact
        ("z", False, 0, None),
        ("b", False, 1, ["Brawl"]),
        ("b:kind", False, 1, ["Brawl:Kindred"]),
        ("b:k", False, 2, ["Brawl:Kindred", "Brawl:Kine"]),
        ("b:kine:kind", False, 1, ["Brawl:Kindred:Kine"]),
        # Exact
        ("z", True, 0, None),
        ("b", True, 0, None),
        ("Brawl", True, 1, ["Brawl"]),
        ("brawl:kindred", True, 1, ["Brawl:Kindred"]),
    ],
)
def test_expansion(
    needle: str,
    exact: bool,
    count: int,
    expectations: list[str],
    skill: VCharTrait,
):
    skill.add_specialties(SPECIALTIES)
    assert len(skill.specialties) == 3

    expansions = skill.expanding(needle, exact)
    assert len(expansions) == count

    for expansion in expansions:
        assert expansion in expectations


@pytest.mark.parametrize(
    "category,allowed",
    [
        (VCharTrait.Type.ATTRIBUTE.value, False),
        (VCharTrait.Type.CUSTOM.value, True),
        (VCharTrait.Type.DISCIPLINE.value, False),
        (VCharTrait.Type.INHERENT.value, False),
        (VCharTrait.Type.SKILL.value, True),
    ],
)
def test_specialties_allowed(category: str, allowed: bool):
    trait = VCharTrait(name="Test", rating=1, type=category)
    assert trait.specialties_allowed == allowed

    if not allowed:
        with pytest.raises(inconnu.errors.SpecialtiesNotAllowed):
            trait.add_specialties("spec")
