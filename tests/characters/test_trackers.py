"""Character tracker tests."""

import pytest

from inconnu.constants import Damage
from inconnu.models import VChar
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
