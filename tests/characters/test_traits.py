"""Character traits tests."""

import pytest

import errors
import tests.characters
from constants import ATTRIBUTES, DISCIPLINES, SKILLS, UNIVERSAL_TRAITS
from models import VChar
from models.vchar import RenameResult
from models.vchardocs import VCharMacro, VCharTrait


@pytest.fixture
def empty_vampire() -> VChar:
    """A dummy vampire with no traits."""
    return tests.characters.gen_char("vampire")


@pytest.fixture
def custom_traits() -> dict[str, int]:
    return {"one": 1, "two": 2, "three": 3}


@pytest.fixture
def vampire(custom_traits: dict[str, int]) -> VChar:
    """A dummy vampire with some custom traits."""
    vamp = tests.characters.gen_char("vampire")
    vamp.assign_traits(custom_traits)
    return vamp


@pytest.mark.parametrize("category", list(VCharTrait.Type))
def test_add_traits(category: VCharTrait.Type, empty_vampire: VChar, custom_traits: dict[str, int]):
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


def test_multiword_find(empty_vampire: VChar):
    """An exact match wins over a longer multiword trait it prefixes, and
    exact lookups don't confuse the two."""
    empty_vampire.assign_traits({"Animal": 1, "Animal Ken": 3})

    assert empty_vampire.find_trait("animal").name == "Animal"
    assert empty_vampire.find_trait("animal ken").name == "Animal Ken"
    assert empty_vampire.find_trait("animal k").name == "Animal Ken"
    with pytest.raises(errors.AmbiguousTraitError):
        _ = empty_vampire.find_trait("anim")

    assert empty_vampire.has_trait("Animal Ken")
    assert not empty_vampire.has_trait("animal k")

    assert empty_vampire.delete_trait("animal") == "Animal"
    assert empty_vampire.has_trait("Animal Ken")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("animalken", "Animal Ken"),
        ("animalk", "Animal Ken"),
        ("bloodsorc", "Blood Sorcery"),
        ("animalken.bigc", "Animal Ken (Big Cats)"),
    ],
)
def test_find_trait_ignores_spaces(name: str, expected: str, empty_vampire: VChar):
    """If nothing matches, find_trait() ignores spaces."""
    empty_vampire.assign_traits({"Animal Ken": 2, "Blood Sorcery": 3})
    empty_vampire.add_specialties("Animal Ken", "Big Cats")

    assert empty_vampire.find_trait(name).name == expected


def test_find_trait_prefers_spaced_matches(empty_vampire: VChar):
    """Ignoring spaces is only a fallback: a match with spaces wins, and an
    ambiguous one stays ambiguous."""
    # assign_traits() would treat Foo Bar as FooBar, so we add them directly
    for name in ("Foo Bar", "Foo Baz", "FooBar"):
        empty_vampire.raw_traits.append(
            VCharTrait(name=name, rating=1, type=VCharTrait.Type.CUSTOM.value)
        )

    assert empty_vampire.find_trait("foobar").name == "FooBar"
    assert empty_vampire.find_trait("foo bar").name == "Foo Bar"
    with pytest.raises(errors.AmbiguousTraitError):
        _ = empty_vampire.find_trait("foo ba")


def test_exact_lookups_ignore_spaces(empty_vampire: VChar):
    """Exact lookups (adding, updating, deleting, specialties) fall back to
    ignoring spaces, so old names still find renamed traits."""
    empty_vampire.assign_traits({"Animal Ken": 2})

    assert empty_vampire.has_trait("AnimalKen")
    assert not empty_vampire.has_trait("AnimalK")

    # Assigning by the old name updates the renamed trait, not a duplicate
    empty_vampire.assign_traits({"AnimalKen": 4})
    assert empty_vampire.find_trait("Animal Ken", True).rating == 4
    assert not any(t.name == "AnimalKen" for t in empty_vampire.raw_traits)

    trait, delta = empty_vampire.add_specialties("animalken", "Big Cats")
    assert trait.name == "Animal Ken"
    assert delta == ["Big Cats"]

    trait, delta = empty_vampire.remove_specialties("ANIMALKEN", "Big Cats")
    assert delta == ["Big Cats"]

    assert empty_vampire.delete_trait("animalken") == "Animal Ken"
    assert not empty_vampire.has_trait("Animal Ken")


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


@pytest.mark.parametrize(
    "input_name,name,trait_type",
    [
        ("BloodSorcery", "Blood Sorcery", VCharTrait.Type.DISCIPLINE),
        ("bloodsorcery", "Blood Sorcery", VCharTrait.Type.DISCIPLINE),
        ("blood sorcery", "Blood Sorcery", VCharTrait.Type.DISCIPLINE),
        ("WatcherValeren", "Watcher Valeren", VCharTrait.Type.DISCIPLINE),
        ("AnimalKen", "Animal Ken", VCharTrait.Type.SKILL),
        ("strength", "Strength", VCharTrait.Type.ATTRIBUTE),
        ("QoNos", "QoNos", VCharTrait.Type.CUSTOM),
    ],
)
def test_standard_names(input_name: str, name: str, trait_type: str, empty_vampire: VChar):
    """New standard traits get their standard names and types, ignoring case
    and spaces. Other new traits are left as given."""
    _, assignments = empty_vampire.assign_traits({input_name: 2})

    assert assignments == {name: 2}
    trait = empty_vampire.traits[0]
    assert trait.name == name
    assert trait.type == trait_type


@pytest.mark.parametrize(
    "auto_trait,expected_type",
    [
        ("Strength", VCharTrait.Type.ATTRIBUTE),
        ("Brawl", VCharTrait.Type.SKILL),
        ("Oblivion", VCharTrait.Type.DISCIPLINE),
    ],
)
def test_auto_category_does_not_leak(
    auto_trait: str, expected_type: VCharTrait.Type, empty_vampire: VChar
):
    """A custom trait assigned alongside an auto-categorized trait stays custom."""
    empty_vampire.assign_traits({auto_trait: 3, "OccultLibrary": 2})

    assert empty_vampire.find_trait(auto_trait).type == expected_type
    assert empty_vampire.find_trait("OccultLibrary").type == VCharTrait.Type.CUSTOM


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


def make_macro(name: str, pool: list[str]) -> VCharMacro:
    """A macro with the given pool."""
    return VCharMacro(
        name=name,
        pool=pool,
        hunger=True,
        difficulty=0,
        rouses=0,
        reroll_rouses=False,
        staining="show",
        hunt=False,
        comment=None,
    )


def test_rename_trait(empty_vampire: VChar):
    """A renamed trait keeps its rating, specialties, and type, stays sorted,
    and is renamed in macros."""
    empty_vampire.assign_traits({"Wits": 2, "QoNos": 3, "Brawl": 1})
    empty_vampire.add_specialties("QoNos", ["Bird of Prey", "Dogs"])
    empty_vampire.macros.append(make_macro("fly", ["Wits", "+", "QoNos.Bird of Prey", "+", "1"]))
    empty_vampire.macros.append(make_macro("punch", ["Brawl", "+", "Wits"]))

    assert empty_vampire.rename_trait("qonos", "Qo'noS") == RenameResult("QoNos", "Qo'noS", 1)

    trait = empty_vampire.find_trait("Qo'noS", True)
    assert trait.rating == 3
    assert trait.type == VCharTrait.Type.CUSTOM
    assert [t.name for t in empty_vampire.traits] == ["Brawl", "Qo'noS", "Wits"]
    assert empty_vampire.traits[1].specialties == ["Bird of Prey", "Dogs"]
    assert empty_vampire.macros[0].pool == ["Wits", "+", "Qo'noS.Bird of Prey", "+", "1"]
    assert empty_vampire.macros[1].pool == ["Brawl", "+", "Wits"]


def test_rename_trait_lookups(empty_vampire: VChar):
    """The old name is found as other lookups find it (ignoring spaces as a
    fallback), and a trait may change only its case."""
    empty_vampire.assign_traits({"Qo Nos": 1})

    assert empty_vampire.rename_trait("qonos", "QO NOS") == RenameResult("Qo Nos", "QO NOS", 0)
    assert empty_vampire.traits[0].name == "QO NOS"


@pytest.mark.parametrize(
    "old,new,error,match",
    [
        ("Missing", "Anything", errors.TraitNotFound, "no trait named `Missing`"),
        ("Night Driving.Rain", "Rain Driving", errors.TraitError, "not specialties"),
        ("Strength", "Might", errors.TraitError, "`Strength` is a standard trait and can't"),
        ("animalken", "Beast Talk", errors.TraitError, "`Animal Ken` is a standard trait and"),
        ("Night Driving", "strength", errors.TraitError, "`Strength` is a standard trait"),
        ("Night Driving", "Big Cats", errors.TraitAlreadyExistsError, "named `Big Cats`"),
        ("Night Driving", "BigCats", errors.TraitAlreadyExistsError, "named `Big Cats`"),
    ],
)
def test_rename_trait_errors(
    old: str, new: str, error: type[Exception], match: str, empty_vampire: VChar
):
    """Standard traits can't be renamed or used as new names, and a new name
    can't belong to another trait."""
    empty_vampire.assign_traits({"Strength": 2, "Animal Ken": 1, "Night Driving": 2, "Big Cats": 1})
    with pytest.raises(error, match=match):
        empty_vampire.rename_trait(old, new)


@pytest.mark.parametrize("new", ["Blood Sorcery", "bloodsorcery", "BLOOD SORCERY"])
def test_rename_to_standard_discipline(new: str, empty_vampire: VChar):
    """Renaming a trait to a standard Discipline gives it the standard
    spelling and type, as adding it would."""
    empty_vampire.raw_traits.append(
        VCharTrait(name="Thaumaturgy", rating=3, type=VCharTrait.Type.CUSTOM.value)
    )

    result = empty_vampire.rename_trait("Thaumaturgy", new)

    assert result == RenameResult("Thaumaturgy", "Blood Sorcery", 0)
    trait = empty_vampire.find_trait("Blood Sorcery", True)
    assert trait.rating == 3
    assert trait.type == VCharTrait.Type.DISCIPLINE
