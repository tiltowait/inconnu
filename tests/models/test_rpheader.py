"""Tests for models/rpheader.py."""

from typing import Any

import pytest
from beanie import PydanticObjectId

from models import VChar
from models.rpheader import HeaderSubdoc
from tests.characters import gen_char


def make_vampire() -> VChar:
    """A saved vampire."""
    vamp = gen_char("vampire")
    vamp.id = PydanticObjectId()
    return vamp


def create(character: VChar, location: str | None) -> HeaderSubdoc:
    """Create a header with only a location override."""
    options: dict[str, Any] = dict.fromkeys(("blush", "merits", "flaws", "temp", "hunger"))
    return HeaderSubdoc.create(character, location=location, **options)


@pytest.mark.parametrize(
    "location,expected",
    [
        ("The Rack", "The Rack"),
        ("Elysium • Roof", "Elysium Roof"),
        ("  The   Rack  ", "The Rack"),
    ],
)
def test_create_cleans_location_override(location: str, expected: str):
    """A location can't add elements to the heading."""
    assert create(make_vampire(), location).location == expected


def test_create_cleans_stored_location():
    """A location saved before bullets were stripped is cleaned too."""
    vamp = make_vampire()
    vamp.header.location = "Elysium • Roof"

    assert create(vamp, None).location == "Elysium Roof"


def test_create_keeps_stored_location():
    """Without an override, the character's location is used."""
    vamp = make_vampire()
    vamp.header.location = "The Rack"

    assert create(vamp, None).location == "The Rack"


def create_with_hunger(character: VChar, hunger: int | None) -> HeaderSubdoc:
    """Create a header with only a Hunger override."""
    options: dict[str, Any] = dict.fromkeys(("blush", "location", "merits", "flaws", "temp"))
    return HeaderSubdoc.create(character, hunger=hunger, **options)


@pytest.mark.parametrize("override,expected", [(None, 3), (0, 0), (5, 5)])
def test_create_hunger_override(override: int | None, expected: int):
    """A Hunger override replaces the character's Hunger, even if it's 0."""
    vamp = make_vampire()
    vamp.hunger = 3

    assert create_with_hunger(vamp, override).hunger == expected


def test_create_ignores_hunger_for_mortals():
    """Mortals have no Hunger to override."""
    mortal = gen_char("mortal")
    mortal.id = PydanticObjectId()

    assert create_with_hunger(mortal, 2).hunger is None
