"""Character-related test package."""

import inconnu


def gen_char(splat: str) -> inconnu.models.VChar:
    """Generate a character with no traits and basic stats."""
    char = inconnu.models.VChar(
        guild=0,
        user=0,
        _name="Dummy",
        splat=splat,
        _humanity=7,
        health=6 * inconnu.constants.Damage.NONE,
        willpower=5 * inconnu.constants.Damage.NONE,
        potency=splat == "vampire" and 1 or 0,
        _traits={},
    )
    char.pre_insert()

    return char
