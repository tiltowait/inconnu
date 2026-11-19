"""Specialty test suite."""

import pytest

import errors
from models.vchardocs import MAX_SUBTRAIT_MATCHES, VCharTrait


@pytest.fixture
def specialties() -> list[str]:
    return ["Kindred", "StreetFighting", "Kine"]


@pytest.fixture
def skill() -> VCharTrait:
    """A basic trait."""
    return VCharTrait(name="Brawl", rating=4, type=VCharTrait.Type.SKILL.value)


@pytest.fixture
def discipline() -> VCharTrait:
    """A basic trait."""
    return VCharTrait(name="Potence", rating=4, type=VCharTrait.Type.DISCIPLINE.value)


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
def test_basic_skill_matching(
    needle: str,
    exact: bool,
    count: int,
    name: str | None,
    rating: int | None,
    skill: VCharTrait,
):
    matches = skill.matching(needle, exact)
    assert len(matches) == count

    if matches:
        assert matches[0].name == name
        assert matches[0].rating == rating


def test_specialty_addition(skill: VCharTrait):
    assert len(skill.specialties) == 0

    skill.add_specialties("Kindred")
    assert len(skill.specialties) == 1

    skill.add_specialties("kindred")  # Also tests case-insensitivity
    assert len(skill.specialties) == 1, "Two 'Kindred' specs were added"

    skill.add_specialties("StreetFighting")
    assert len(skill.specialties) == 2, "'StreetFighting' wasn't added"

    skill.add_specialties(["One", "Two", "Two"])
    assert len(skill.specialties) == 4, "List wasn't added"


def test_alphabetic_specialties(skill: VCharTrait):
    skill.add_specialties(["Kine", "Kindred", "Apples"])
    skill.add_specialties("Blip")
    assert skill.specialties == ["Apples", "Blip", "Kindred", "Kine"]


def test_case_insensitive(skill: VCharTrait):
    skill.add_specialties(["Kine"])
    assert len(skill.specialties) == 1
    assert skill.specialties[0] == "Kine"

    skill.add_specialties(["kine"])
    assert len(skill.specialties) == 1
    assert skill.specialties[0] == "Kine"


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
        (".z", False, 0, None),
        (".k.z", False, 0, None),
        ("b.kind", False, 1, [("Brawl (Kindred)", 5, False, "Brawl.Kindred")]),
        (".kind", False, 1, [("Brawl (Kindred)", 5, False, "Brawl.Kindred")]),
        ("brawl.kindred", False, 1, [("Brawl (Kindred)", 5, True, "Brawl.Kindred")]),
        (
            ".k",
            False,
            2,
            [
                ("Brawl (Kindred)", 5, False, "Brawl.Kindred"),
                ("Brawl (Kine)", 5, False, "Brawl.Kine"),
            ],
        ),
        (
            ".kind.s",
            False,
            1,
            [("Brawl (Kindred, StreetFighting)", 6, False, "Brawl.Kindred.StreetFighting")],
        ),
        # Exact
        ("Brawl", True, 1, [("Brawl", 4, True, "Brawl")]),
        ("brawl", True, 1, [("Brawl", 4, True, "Brawl")]),
        ("b", True, 0, None),
        ("brawl.kindred", True, 1, [("Brawl (Kindred)", 5, True, "Brawl.Kindred")]),
        ("brawl.kin", True, 0, None),
        (
            "Brawl.Kindred.StreetFighting",
            True,
            1,
            [("Brawl (Kindred, StreetFighting)", 6, True, "Brawl.Kindred.StreetFighting")],
        ),
        (":kindred", True, 0, None),
    ],
)
def test_specialty_matching(
    needle: str,
    exact: bool,
    count: int,
    expectations: list[tuple[str, int, bool, str]],
    skill: VCharTrait,
    specialties: list[str],
):
    skill.add_specialties(specialties)
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
        ("b.kind", False, 1, ["Brawl.Kindred"]),
        ("b.k", False, 2, ["Brawl.Kindred", "Brawl.Kine"]),
        ("b.kine.kind", False, 1, ["Brawl.Kindred.Kine"]),
        # Exact
        ("z", True, 0, None),
        ("b", True, 0, None),
        ("Brawl", True, 1, ["Brawl"]),
        ("brawl.kindred", True, 1, ["Brawl.Kindred"]),
    ],
)
def test_expansion(
    needle: str,
    exact: bool,
    count: int,
    expectations: list[str],
    skill: VCharTrait,
    specialties: list[str],
):
    skill.add_specialties(specialties)
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
        with pytest.raises(errors.SpecialtiesNotAllowed):
            trait.add_specialties("spec")


def test_subtrait_delineation(skill: VCharTrait, discipline: VCharTrait):
    skill.add_specialties("Kindred")
    discipline.add_powers("Prowess")

    with pytest.raises(errors.SpecialtiesNotAllowed):
        skill.add_powers("Prowess")
    with pytest.raises(errors.SpecialtiesNotAllowed):
        discipline.add_specialties("Kindred")


# Multiword names


@pytest.fixture
def multiword() -> VCharTrait:
    """A multiword skill with multiword specialties."""
    trait = VCharTrait(name="Animal Ken", rating=3, type=VCharTrait.Type.SKILL.value)
    trait.add_specialties(["Big Cats", "Big Game", "Dogs"])
    return trait


@pytest.mark.parametrize(
    "needle,exact,expected",
    [
        # Only the last word abbreviates
        ("animal ken", False, [("Animal Ken", 3, True, "Animal Ken")]),
        ("Animal K", False, [("Animal Ken", 3, False, "Animal Ken")]),
        ("animal", False, [("Animal Ken", 3, False, "Animal Ken")]),
        ("an k", False, []),
        ("animalken", False, []),
        ("animal  ken", False, []),
        # Specialties
        ("animal ken.big cats", False, [("Animal Ken (Big Cats)", 4, True, "Animal Ken.Big Cats")]),
        ("an.big c", False, [("Animal Ken (Big Cats)", 4, False, "Animal Ken.Big Cats")]),
        (
            "animal ken.big",
            False,
            [
                ("Animal Ken (Big Cats)", 4, False, "Animal Ken.Big Cats"),
                ("Animal Ken (Big Game)", 4, False, "Animal Ken.Big Game"),
            ],
        ),
        ("animal ken.b c", False, []),
        # Specialties sort, and exactness ignores their order
        (
            "animal ken.dogs.big cats",
            False,
            [("Animal Ken (Big Cats, Dogs)", 5, True, "Animal Ken.Big Cats.Dogs")],
        ),
        # Exact
        ("animal ken", True, [("Animal Ken", 3, True, "Animal Ken")]),
        ("animal", True, []),
        ("animal ken.big cats", True, [("Animal Ken (Big Cats)", 4, True, "Animal Ken.Big Cats")]),
        ("animal ken.big", True, []),
    ],
)
def test_multiword_matching(
    needle: str,
    exact: bool,
    expected: list[tuple[str, int, bool, str]],
    multiword: VCharTrait,
):
    """Multiword names match by prefix of the whole name, like single words."""
    matches = multiword.matching(needle, exact)
    assert [(m.name, m.rating, m.exact, m.key) for m in matches] == expected


@pytest.mark.parametrize(
    "needle,expected",
    [
        ("animal k", ["Animal Ken"]),
        ("animal ken.big", ["Animal Ken.Big Cats", "Animal Ken.Big Game"]),
        ("animal ken.big g.d", ["Animal Ken.Big Game.Dogs"]),
        ("animal ken.big.big", ["Animal Ken.Big Cats.Big Game"]),
    ],
)
def test_multiword_expansion(needle: str, expected: list[str], multiword: VCharTrait):
    """Multiword specialties expand to their full names."""
    assert sorted(multiword.expanding(needle, False)) == expected


@pytest.mark.parametrize(
    "needle,exact,expected",
    [
        ("animalken", False, [("Animal Ken", 3, True, "Animal Ken")]),
        ("animalk", False, [("Animal Ken", 3, False, "Animal Ken")]),
        ("animal ken", False, [("Animal Ken", 3, True, "Animal Ken")]),
        ("animalken.bigcats", False, [("Animal Ken (Big Cats)", 4, True, "Animal Ken.Big Cats")]),
        ("animalk.bigc", False, [("Animal Ken (Big Cats)", 4, False, "Animal Ken.Big Cats")]),
        ("AnimalKen", True, [("Animal Ken", 3, True, "Animal Ken")]),
        ("animalk", True, []),
    ],
)
def test_matching_ignoring_spaces(
    needle: str,
    exact: bool,
    expected: list[tuple[str, int, bool, str]],
    multiword: VCharTrait,
):
    """With ignore_spaces, names match without their spaces."""
    matches = multiword.matching(needle, exact, ignore_spaces=True)
    assert [(m.name, m.rating, m.exact, m.key) for m in matches] == expected


@pytest.mark.parametrize("needle", ["animalken", "animalk", "animalken.bigcats"])
def test_matching_spaces_by_default(needle: str, multiword: VCharTrait):
    """By default, spaces count."""
    assert not multiword.matching(needle, False)


def test_repeated_specialty_tokens_merge(skill: VCharTrait):
    """Tokens matching the same specialties merge into distinct selections, so
    repeating a token can't multiply the work."""
    skill.add_specialties(["Kindred", "Kine", "Kinfolk"])

    assert skill.expanding("b.k.k", False) == [
        "Brawl.Kindred.Kine",
        "Brawl.Kindred.Kinfolk",
        "Brawl.Kine.Kinfolk",
    ]
    assert skill.expanding("b.k.k.k", False) == ["Brawl.Kindred.Kine.Kinfolk"]


def test_long_exact_specialty_lists(skill: VCharTrait):
    """Exact specialties narrow to one combination, however many there are,
    so stored macro keys of any length still match."""
    specs = [f"Spec{letter}" for letter in "ABCDEFGH"]
    skill.add_specialties(specs)

    key = "Brawl." + ".".join(specs)
    assert skill.expanding(key.lower(), False) == [key]


def test_vague_specialties_are_capped(skill: VCharTrait):
    """Vague input that matches many combinations keeps only the first
    MAX_SUBTRAIT_MATCHES, in order."""
    skill.add_specialties([f"Spec{letter}" for letter in "ABCDEFGHIJ"])

    matches = skill.expanding("brawl" + ".spec" * 5, False)  # 252 combinations
    assert len(matches) == MAX_SUBTRAIT_MATCHES
    assert matches == sorted(matches)
    assert matches[0] == "Brawl.SpecA.SpecB.SpecC.SpecD.SpecE"
