"""Test VChar properties and methods."""

import pytest

import errors
from inconnu.constants import Damage
from models import VChar


@pytest.fixture
def vampire() -> VChar:
    """Create a vampire character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Vampire",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=2,
    )
    char.pre_insert()
    return char


@pytest.fixture
def thin_blood() -> VChar:
    """Create a thin-blood character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Thinblood",
        splat="thin-blood",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    char.pre_insert()
    return char


@pytest.fixture
def mortal() -> VChar:
    """Create a mortal character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Mortal",
        splat="mortal",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    char.pre_insert()
    return char


@pytest.fixture
def ghoul() -> VChar:
    """Create a ghoul character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Ghoul",
        splat="ghoul",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    char.pre_insert()
    return char


# MACRO SYSTEM TESTS


def test_find_macro(vampire):
    """Test finding a macro by name."""
    vampire.add_macro(
        name="TestMacro",
        pool=["Strength", "Brawl"],
        hunger=True,
        difficulty=3,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment="Test comment",
    )

    macro = vampire.find_macro("TestMacro")
    assert macro.name == "TestMacro"
    assert macro.pool == ["Strength", "Brawl"]
    assert macro.difficulty == 3
    assert macro.hunger is True


def test_find_macro_case_insensitive(vampire):
    """Test that macro lookup is case-insensitive."""
    vampire.add_macro(
        name="TestMacro",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    # All of these should find the macro
    assert vampire.find_macro("TestMacro").name == "TestMacro"
    assert vampire.find_macro("testmacro").name == "TestMacro"
    assert vampire.find_macro("TESTMACRO").name == "TestMacro"
    assert vampire.find_macro("TeStMaCrO").name == "TestMacro"


def test_find_macro_not_found(vampire):
    """Test that finding a non-existent macro raises MacroNotFoundError."""
    with pytest.raises(errors.MacroNotFoundError):
        vampire.find_macro("NonExistent")


def test_add_macro(vampire):
    """Test adding a macro to a character."""
    assert len(vampire.macros) == 0

    vampire.add_macro(
        name="NewMacro",
        pool=["Dexterity", "Stealth"],
        hunger=False,
        difficulty=4,
        rouses=1,
        reroll_rouses=True,
        staining="prowess",
        hunt=False,
        comment="Sneaky stuff",
    )

    assert len(vampire.macros) == 1
    macro = vampire.macros[0]
    assert macro.name == "NewMacro"
    assert macro.pool == ["Dexterity", "Stealth"]
    assert macro.difficulty == 4
    assert macro.rouses == 1
    assert macro.reroll_rouses is True
    assert macro.staining == "prowess"
    assert macro.comment == "Sneaky stuff"


def test_add_macro_duplicate_raises_error(vampire):
    """Test that adding a duplicate macro raises MacroAlreadyExistsError."""
    vampire.add_macro(
        name="Duplicate",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    with pytest.raises(errors.MacroAlreadyExistsError):
        vampire.add_macro(
            name="Duplicate",
            pool=["Dexterity"],
            hunger=False,
            difficulty=3,
            rouses=0,
            reroll_rouses=False,
            staining="",
            hunt=False,
            comment=None,
        )


def test_add_macro_sorting(vampire):
    """Test that macros are sorted alphabetically by name."""
    vampire.add_macro(
        name="Zebra",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    vampire.add_macro(
        name="Alpha",
        pool=["Dexterity"],
        hunger=False,
        difficulty=3,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    vampire.add_macro(
        name="Middle",
        pool=["Wits"],
        hunger=False,
        difficulty=4,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    assert vampire.macros[0].name == "Alpha"
    assert vampire.macros[1].name == "Middle"
    assert vampire.macros[2].name == "Zebra"


def test_update_macro(vampire):
    """Test updating a macro's properties."""
    vampire.add_macro(
        name="UpdateMe",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment="Original",
    )

    # Update difficulty
    vampire.update_macro("UpdateMe", {"difficulty": 5})
    macro = vampire.find_macro("UpdateMe")
    assert macro.difficulty == 5
    assert macro.comment == "Original"  # Other fields unchanged

    # Update pool and comment
    vampire.update_macro("UpdateMe", {"pool": ["Dexterity", "Stealth"], "comment": "Updated"})
    macro = vampire.find_macro("UpdateMe")
    assert macro.pool == ["Dexterity", "Stealth"]
    assert macro.comment == "Updated"
    assert macro.difficulty == 5  # Previously updated field retained


def test_update_macro_name_resorts(vampire):
    """Test that renaming a macro re-sorts the list."""
    vampire.add_macro(
        name="Aaa",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    vampire.add_macro(
        name="Bbb",
        pool=["Dexterity"],
        hunger=False,
        difficulty=3,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    vampire.add_macro(
        name="Ccc",
        pool=["Wits"],
        hunger=False,
        difficulty=4,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    # Rename "Aaa" to "Zzz"
    new_name = vampire.update_macro("Aaa", {"name": "Zzz"})
    assert new_name == "Zzz"

    # Check new order
    assert vampire.macros[0].name == "Bbb"
    assert vampire.macros[1].name == "Ccc"
    assert vampire.macros[2].name == "Zzz"


def test_update_macro_not_found(vampire):
    """Test that updating a non-existent macro raises MacroNotFoundError."""
    with pytest.raises(errors.MacroNotFoundError):
        vampire.update_macro("NonExistent", {"difficulty": 5})


def test_delete_macro(vampire):
    """Test deleting a macro."""
    vampire.add_macro(
        name="DeleteMe",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    vampire.add_macro(
        name="KeepMe",
        pool=["Dexterity"],
        hunger=False,
        difficulty=3,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    assert len(vampire.macros) == 2

    vampire.delete_macro("DeleteMe")
    assert len(vampire.macros) == 1
    assert vampire.macros[0].name == "KeepMe"

    # Verify it's really gone
    with pytest.raises(errors.MacroNotFoundError):
        vampire.find_macro("DeleteMe")


def test_delete_macro_case_insensitive(vampire):
    """Test that macro deletion is case-insensitive."""
    vampire.add_macro(
        name="TestMacro",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )

    vampire.delete_macro("testmacro")
    assert len(vampire.macros) == 0


def test_delete_macro_not_found(vampire):
    """Test that deleting a non-existent macro raises MacroNotFoundError."""
    with pytest.raises(errors.MacroNotFoundError):
        vampire.delete_macro("NonExistent")


# VAMPIRE-SPECIFIC PROPERTY TESTS


@pytest.mark.parametrize(
    "potency,expected_surge",
    [
        (0, 1),  # ceil(0/2) + 1 = 1
        (1, 2),  # ceil(1/2) + 1 = 2
        (2, 2),  # ceil(2/2) + 1 = 2
        (3, 3),  # ceil(3/2) + 1 = 3
        (4, 3),  # ceil(4/2) + 1 = 3
        (5, 4),  # ceil(5/2) + 1 = 4
        (6, 4),  # ceil(6/2) + 1 = 4
        (7, 5),  # ceil(7/2) + 1 = 5
        (8, 5),  # ceil(8/2) + 1 = 5
        (9, 6),  # ceil(9/2) + 1 = 6
        (10, 6),  # ceil(10/2) + 1 = 6
    ],
)
def test_surge(potency, expected_surge, vampire):
    """Test Blood Surge calculation based on potency."""
    vampire.potency = potency
    assert vampire.surge == expected_surge


@pytest.mark.parametrize(
    "potency,expected_bane",
    [
        (0, 0),  # Potency 0 = no bane
        (1, 2),  # ceil(1/2) + 1 = 2
        (2, 2),  # ceil(2/2) + 1 = 2
        (3, 3),  # ceil(3/2) + 1 = 3
        (4, 3),  # ceil(4/2) + 1 = 3
        (5, 4),  # ceil(5/2) + 1 = 4
        (6, 4),  # ceil(6/2) + 1 = 4
        (7, 5),  # ceil(7/2) + 1 = 5
        (8, 5),  # ceil(8/2) + 1 = 5
        (9, 6),  # ceil(9/2) + 1 = 6
        (10, 6),  # ceil(10/2) + 1 = 6
    ],
)
def test_bane_severity(potency, expected_bane, vampire):
    """Test bane severity calculation based on potency."""
    vampire.potency = potency
    assert vampire.bane_severity == expected_bane
    assert vampire.bane == expected_bane  # Shorthand property


@pytest.mark.parametrize(
    "potency,expected_bonus",
    [
        (0, 0),  # 0 // 2 = 0
        (1, 0),  # 1 // 2 = 0
        (2, 1),  # 2 // 2 = 1
        (3, 1),  # 3 // 2 = 1
        (4, 2),  # 4 // 2 = 2
        (5, 2),  # 5 // 2 = 2
        (6, 3),  # 6 // 2 = 3
        (7, 3),  # 7 // 2 = 3
        (8, 4),  # 8 // 2 = 4
        (9, 4),  # 9 // 2 = 4
        (10, 5),  # 10 // 2 = 5
    ],
)
def test_power_bonus(potency, expected_bonus, vampire):
    """Test power bonus calculation based on potency."""
    vampire.potency = potency
    assert vampire.power_bonus == expected_bonus


def test_power_bonus_nonvampire(mortal):
    """Test that non-vampires have no power bonus."""
    mortal.potency = 5  # Shouldn't matter
    assert mortal.power_bonus == 0


@pytest.mark.parametrize(
    "potency,expected_mend",
    [
        (0, 1),
        (1, 1),
        (2, 2),
        (3, 2),
        (4, 3),
        (5, 3),
        (6, 3),
        (7, 3),
        (8, 4),
        (9, 4),
        (10, 5),
    ],
)
def test_mend_amount_vampire(potency, expected_mend, vampire):
    """Test mend amount for vampires based on potency."""
    vampire.potency = potency
    assert vampire.mend_amount == expected_mend


def test_mend_amount_mortal(mortal):
    """Test mend amount for mortals based on Stamina."""
    # Mortals use Stamina rating
    mortal.assign_traits({"Stamina": 3})
    assert mortal.mend_amount == 3

    mortal.assign_traits({"Stamina": 5})
    assert mortal.mend_amount == 5


def test_mend_amount_ghoul(ghoul):
    """Test mend amount for ghouls based on Stamina."""
    ghoul.assign_traits({"Stamina": 4})
    assert ghoul.mend_amount == 4


# WILLPOWER RECOVERY TESTS


def test_willpower_recovery_no_traits(vampire):
    """Test willpower recovery when character has no Resolve or Composure."""
    # Default is max(0, 0) = 0
    assert vampire.willpower_recovery == 0


def test_willpower_recovery_resolve_only(vampire):
    """Test willpower recovery with only Resolve."""
    vampire.assign_traits({"Resolve": 3})
    assert vampire.willpower_recovery == 3


def test_willpower_recovery_composure_only(vampire):
    """Test willpower recovery with only Composure."""
    vampire.assign_traits({"Composure": 4})
    assert vampire.willpower_recovery == 4


def test_willpower_recovery_both_traits(vampire):
    """Test willpower recovery with both Resolve and Composure."""
    vampire.assign_traits({"Resolve": 2, "Composure": 5})
    # Should return max(2, 5) = 5
    assert vampire.willpower_recovery == 5

    vampire.assign_traits({"Resolve": 4, "Composure": 3})
    # Should return max(4, 3) = 4
    assert vampire.willpower_recovery == 4


def test_willpower_recovery_equal_traits(vampire):
    """Test willpower recovery when Resolve and Composure are equal."""
    vampire.assign_traits({"Resolve": 3, "Composure": 3})
    assert vampire.willpower_recovery == 3


def test_willpower_recovery_mortal(mortal):
    """Test willpower recovery for mortals."""
    mortal.assign_traits({"Resolve": 2, "Composure": 4})
    assert mortal.willpower_recovery == 4


def test_willpower_recovery_trait_not_found_handled(vampire):
    """Test that TraitNotFound is handled gracefully."""
    # Even though the character has no Resolve or Composure,
    # the property should handle the exception and return max(0, 0)
    try:
        recovery = vampire.willpower_recovery
        assert recovery == 0
    except errors.TraitNotFound:
        pytest.fail("willpower_recovery should handle TraitNotFound gracefully")


# FRENZY RESIST TESTS


def test_frenzy_resist_full_willpower(vampire):
    """Test frenzy resist with full willpower."""
    # Willpower = 5 (all undamaged)
    # Humanity = 7
    # Formula: max(current_wp + humanity/3, 1)
    # = max(5 + 2, 1) = 7
    assert vampire.frenzy_resist == 7


def test_frenzy_resist_damaged_willpower(vampire):
    """Test frenzy resist with damaged willpower."""
    vampire.apply_damage("willpower", Damage.SUPERFICIAL, 3)
    # Current WP = 2
    # Humanity = 7, 7/3 = 2
    # = max(2 + 2, 1) = 4
    assert vampire.frenzy_resist == 4


def test_frenzy_resist_no_willpower(vampire):
    """Test frenzy resist with no willpower left."""
    vampire.apply_damage("willpower", Damage.SUPERFICIAL, 5)
    # Current WP = 0
    # Humanity = 7, 7/3 = 2
    # = max(0 + 2, 1) = 2
    assert vampire.frenzy_resist == 2


def test_frenzy_resist_minimum_one(vampire):
    """Test that frenzy resist is always at least 1."""
    vampire.apply_damage("willpower", Damage.SUPERFICIAL, 5)
    vampire.humanity = 0
    # Current WP = 0
    # Humanity = 0, 0/3 = 0
    # = max(0 + 0, 1) = 1
    assert vampire.frenzy_resist == 1


@pytest.mark.parametrize(
    "humanity,expected_third",
    [
        (10, 3),  # 10/3 = 3.33 -> 3
        (9, 3),  # 9/3 = 3
        (8, 2),  # 8/3 = 2.66 -> 2
        (7, 2),  # 7/3 = 2.33 -> 2
        (6, 2),  # 6/3 = 2
        (5, 1),  # 5/3 = 1.66 -> 1
        (4, 1),  # 4/3 = 1.33 -> 1
        (3, 1),  # 3/3 = 1
        (2, 0),  # 2/3 = 0.66 -> 0
        (1, 0),  # 1/3 = 0.33 -> 0
        (0, 0),  # 0/3 = 0
    ],
)
def test_frenzy_resist_humanity_values(humanity, expected_third, vampire):
    """Test frenzy resist calculation with different Humanity values."""
    vampire.humanity = humanity
    current_wp = vampire.willpower.count(Damage.NONE)
    expected = max(current_wp + expected_third, 1)
    assert vampire.frenzy_resist == expected
