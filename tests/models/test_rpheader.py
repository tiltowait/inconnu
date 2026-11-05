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
