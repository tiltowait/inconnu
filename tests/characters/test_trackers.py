"""Character tracker tests."""

import pytest

from inconnu.constants import Damage
from models import VChar
from tests.characters import gen_char


@pytest.fixture(params=["vampire", "ghoul", "mortal", "thin-blood"])
def character(request) -> VChar:
    return gen_char(request.param)


def test_hunger(character: VChar):
    if character.is_vampire:
        assert character.hunger == 1

        # Test clamping
        character.hunger = 3
        assert character.hunger == 3
        character.hunger = 30
        assert character.hunger == 5, "Hunger should have clamped to 5"
        character.hunger = -3
        assert character.hunger == 0, "Hunger should have clamped to 0"

    else:
        assert character.hunger == 0
        character.hunger = 4
        assert character.hunger == 0, "Non-vampires should have zero Hunger"


def test_apply_damage(character: VChar):
    """Test damage application and wrapping."""
    character.apply_damage("health", Damage.SUPERFICIAL, 3)
    assert character.health == "...///"

    character.apply_damage("health", Damage.AGGRAVATED, 1)
    assert character.health == "..///x"

    character.apply_damage("health", Damage.SUPERFICIAL, 2)
    assert character.health == "/////x"
    assert character.physically_impaired
    assert not character.mentally_impaired

    character.apply_damage("health", Damage.SUPERFICIAL, 2)
    assert character.health == "///xxx"
    assert character.superficial_hp == 3
    assert character.aggravated_hp == 3

    character.apply_damage("willpower", Damage.SUPERFICIAL, 8)
    assert character.willpower == "//xxx"
    assert character.superficial_wp == 2
    assert character.aggravated_wp == 3
    assert character.mentally_impaired


def test_set_damage(character: VChar):
    """Test the set_damage() method."""
    character.set_damage("health", Damage.SUPERFICIAL, 3)
    assert character.health == "...///"

    character.set_damage("health", Damage.SUPERFICIAL, 20)
    assert character.health == "//////"

    character.set_damage("health", Damage.AGGRAVATED, 1)
    assert character.health == "/////x"

    character.set_damage("health", Damage.AGGRAVATED, 0)
    assert character.health == "./////"


def test_humanity(character: VChar):
    """Test Humanity calculations."""
    assert character.humanity == 7
    assert character.stains == 0

    character.stains += 2
    assert character.humanity == 7
    assert character.stains == 2

    assert not character.degeneration

    character.stains += 2
    assert character.degeneration

    character.humanity -= 1
    assert character.humanity == 6
    assert character.stains == 0


@pytest.mark.parametrize(
    "tracker, damage, impairment",
    [
        ["health", Damage.AGGRAVATED, ""],  # Depends on char type
        ["health", Damage.SUPERFICIAL, "physically"],
        ["willpower", Damage.SUPERFICIAL, "mentally"],
    ],
)
def test_impairment(tracker: str, damage: Damage, impairment: str, character: VChar):
    assert character.impairment is None, "Character should start with no impairment"

    character.set_damage(tracker, damage, 20)
    if tracker == "health" and damage == Damage.AGGRAVATED:
        if character.is_vampire:
            assert "TORPOR" in character.impairment, "Vampire should be in torpor"
        else:
            assert "DEAD" in character.impairment, "Human should be dead"
    else:
        assert impairment in character.impairment


@pytest.mark.parametrize("attribute", ["Resolve", "Composure", "Stamina"])
def test_tracker_trait_update(attribute: str, character: VChar):
    """Ensure that trait updates properly update trackers."""

    def rating(tracker: str):
        """The character's tracker rating."""
        return len(getattr(character, tracker))

    assert not character.has_trait(attribute)

    if attribute in ["Resolve", "Composure"]:
        tracker = "willpower"
    else:
        tracker = "health"

    base_rating = rating(tracker)
    character.assign_traits({attribute: 2, "Test": 1})
    assert base_rating == rating(tracker), "Initial set should not modify the tracker"

    character.assign_traits({attribute: 4})
    assert rating(tracker) == base_rating + 2

    character.assign_traits({attribute: 1})
    assert rating(tracker) == base_rating - 1

    current = rating(tracker)
    character.assign_traits({"Test": 2})
    assert current == rating(tracker), "Other trait shouldn't trigger update"


# SET_AGGRAVATED_HP TESTS


def test_set_aggravated_hp_basic(character: VChar):
    """Test setting aggravated health damage."""
    assert character.aggravated_hp == 0
    assert character.health == "......"

    character.set_aggravated_hp(2)
    assert character.aggravated_hp == 2
    assert character.health == "....xx"


def test_set_aggravated_hp_zero(character: VChar):
    """Test setting aggravated health to zero."""
    character.apply_damage("health", Damage.AGGRAVATED, 3)
    assert character.aggravated_hp == 3

    character.set_aggravated_hp(0)
    assert character.aggravated_hp == 0
    assert character.health == "......"


def test_set_aggravated_hp_increase(character: VChar):
    """Test increasing aggravated health damage."""
    character.set_aggravated_hp(1)
    assert character.aggravated_hp == 1

    character.set_aggravated_hp(3)
    assert character.aggravated_hp == 3


def test_set_aggravated_hp_decrease(character: VChar):
    """Test decreasing aggravated health damage."""
    character.set_aggravated_hp(4)
    assert character.aggravated_hp == 4

    character.set_aggravated_hp(2)
    assert character.aggravated_hp == 2


def test_set_aggravated_hp_with_superficial(character: VChar):
    """Test setting aggravated HP when superficial damage exists."""
    # Add superficial damage first
    character.apply_damage("health", Damage.SUPERFICIAL, 2)
    assert character.superficial_hp == 2
    assert character.health == "....//"

    # Now set aggravated
    character.set_aggravated_hp(2)
    assert character.aggravated_hp == 2
    assert character.superficial_hp == 2
    assert character.health == "..//xx"


def test_set_aggravated_hp_overwrites_superficial(character: VChar):
    """Test that setting high aggravated can overwrite superficial."""
    character.apply_damage("health", Damage.SUPERFICIAL, 3)
    assert character.superficial_hp == 3

    # Set aggravated to 5 - should push out superficial
    character.set_aggravated_hp(5)
    assert character.aggravated_hp == 5
    assert character.superficial_hp == 1
    assert character.health == "/xxxxx"


def test_set_aggravated_hp_no_wrap(character: VChar):
    """Test that set_aggravated_hp doesn't wrap (overflow becomes aggravated)."""
    # Try to set more aggravated than the tracker allows
    character.set_aggravated_hp(10)
    # Should cap at tracker length (6)
    assert character.aggravated_hp == 6
    assert character.health == "xxxxxx"


def test_set_aggravated_hp_multiple_times(character: VChar):
    """Test setting aggravated HP multiple times."""
    character.set_aggravated_hp(1)
    assert character.aggravated_hp == 1

    character.set_aggravated_hp(3)
    assert character.aggravated_hp == 3

    character.set_aggravated_hp(2)
    assert character.aggravated_hp == 2

    character.set_aggravated_hp(0)
    assert character.aggravated_hp == 0


def test_set_aggravated_hp_full_tracker(character: VChar):
    """Test setting aggravated HP to fill the entire tracker."""
    character.set_aggravated_hp(6)
    assert character.aggravated_hp == 6
    assert character.superficial_hp == 0
    assert character.health == "xxxxxx"

    if character.is_vampire:
        assert "TORPOR" in character.impairment
    else:
        assert "DEAD" in character.impairment


def test_set_aggravated_hp_preserves_superficial_order(character: VChar):
    """Test that superficial damage stays on the left when setting aggravated."""
    character.set_aggravated_hp(2)
    character.apply_damage("health", Damage.SUPERFICIAL, 2)

    assert character.health == "..//xx"
    assert character.superficial_hp == 2
    assert character.aggravated_hp == 2


# SET_SUPERFICIAL_WP TESTS


def test_set_superficial_wp_basic(character: VChar):
    """Test setting superficial willpower damage."""
    assert character.superficial_wp == 0
    assert character.willpower == "....."

    character.set_superficial_wp(2)
    assert character.superficial_wp == 2
    assert character.willpower == "...//"


def test_set_superficial_wp_zero(character: VChar):
    """Test setting superficial willpower to zero."""
    character.apply_damage("willpower", Damage.SUPERFICIAL, 3)
    assert character.superficial_wp == 3

    character.set_superficial_wp(0)
    assert character.superficial_wp == 0
    assert character.willpower == "....."


def test_set_superficial_wp_increase(character: VChar):
    """Test increasing superficial willpower damage."""
    character.set_superficial_wp(1)
    assert character.superficial_wp == 1

    character.set_superficial_wp(3)
    assert character.superficial_wp == 3


def test_set_superficial_wp_decrease(character: VChar):
    """Test decreasing superficial willpower damage."""
    character.set_superficial_wp(4)
    assert character.superficial_wp == 4

    character.set_superficial_wp(2)
    assert character.superficial_wp == 2


def test_set_superficial_wp_with_aggravated(character: VChar):
    """Test setting superficial WP when aggravated damage exists."""
    # Add aggravated damage first
    character.apply_damage("willpower", Damage.AGGRAVATED, 1)
    assert character.aggravated_wp == 1
    assert character.willpower == "....x"

    # Now set superficial
    character.set_superficial_wp(2)
    assert character.superficial_wp == 2
    assert character.aggravated_wp == 1
    assert character.willpower == "..//x"


def test_set_superficial_wp_wraps_to_aggravated(character: VChar):
    """Test that set_superficial_wp wraps overflow into aggravated."""
    # Set superficial to more than the tracker holds
    character.set_superficial_wp(8)

    # Tracker is 5, so 8 superficial should become 5 superficial + 3 aggravated
    # But wrapping means: 5 total - (8 sup) = overflow of 3 becomes aggravated
    # Result: as much superficial as fits, overflow becomes aggravated
    assert character.superficial_wp == 2
    assert character.aggravated_wp == 3
    assert character.willpower == "//xxx"


def test_set_superficial_wp_multiple_times(character: VChar):
    """Test setting superficial WP multiple times."""
    character.set_superficial_wp(1)
    assert character.superficial_wp == 1

    character.set_superficial_wp(3)
    assert character.superficial_wp == 3

    character.set_superficial_wp(2)
    assert character.superficial_wp == 2

    character.set_superficial_wp(0)
    assert character.superficial_wp == 0


def test_set_superficial_wp_full_tracker(character: VChar):
    """Test setting superficial WP to fill the entire tracker."""
    character.set_superficial_wp(5)
    assert character.superficial_wp == 5
    assert character.aggravated_wp == 0
    assert character.willpower == "/////"
    assert character.mentally_impaired


def test_set_superficial_wp_extreme_overflow(character: VChar):
    """Test setting superficial WP to extreme values that overflow."""
    character.set_superficial_wp(20)

    # All becomes aggravated due to wrapping
    assert character.aggravated_wp == 5
    assert character.superficial_wp == 0
    assert character.willpower == "xxxxx"


def test_set_superficial_wp_with_existing_aggravated(character: VChar):
    """Test superficial wrapping with existing aggravated damage."""
    # Set 2 aggravated first
    character.apply_damage("willpower", Damage.AGGRAVATED, 2)
    assert character.willpower == "...xx"

    # Now set 4 superficial - should wrap 1 into aggravated
    character.set_superficial_wp(4)
    # Tracker: 5 total, 4 sup + 2 agg = 6, so 1 wraps -> 2 sup + 3 agg
    assert character.superficial_wp == 2
    assert character.aggravated_wp == 3
    assert character.willpower == "//xxx"


def test_set_superficial_wp_preserves_aggravated_order(character: VChar):
    """Test that aggravated damage stays on the right when setting superficial."""
    character.apply_damage("willpower", Damage.AGGRAVATED, 1)
    character.set_superficial_wp(2)

    assert character.willpower == "..//x"
    assert character.superficial_wp == 2
    assert character.aggravated_wp == 1


# CROSS-FUNCTION INTERACTION TESTS


def test_aggravated_hp_and_superficial_wp_independent(character: VChar):
    """Test that health and willpower damage are independent."""
    character.set_aggravated_hp(2)
    character.set_superficial_wp(3)

    assert character.aggravated_hp == 2
    assert character.superficial_wp == 3
    assert character.health == "....xx"
    assert character.willpower == "..///"


def test_set_aggravated_hp_then_apply_damage(character: VChar):
    """Test that set_aggravated_hp works correctly before apply_damage."""
    character.set_aggravated_hp(1)
    character.apply_damage("health", Damage.SUPERFICIAL, 2)

    assert character.aggravated_hp == 1
    assert character.superficial_hp == 2
    assert character.health == "...//x"


def test_set_superficial_wp_then_apply_damage(character: VChar):
    """Test that set_superficial_wp works correctly before apply_damage."""
    character.set_superficial_wp(2)
    character.apply_damage("willpower", Damage.AGGRAVATED, 1)

    assert character.superficial_wp == 2
    assert character.aggravated_wp == 1
    assert character.willpower == "..//x"
