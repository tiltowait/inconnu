"""Character-related test package."""

import constants
from models import VChar


def gen_char(splat: str) -> VChar:
    """Generate a character with no traits and basic stats."""
    char = VChar(
        guild=0,
        user=0,
        raw_name="Dummy",
        splat=splat,
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=splat == "vampire" and 1 or 0,
    )
    char.pre_insert()

    return char
