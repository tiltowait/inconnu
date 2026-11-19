"""Validation utilities for character data."""

import re

from constants import RESERVED_TRAITS, Damage
from utils.text import pluralize

VALID_TRAIT_PATTERN = re.compile(r"^[A-Za-z_]+$")
MAX_NAME_LENGTH = 30  # Character names
MAX_TRAIT_LENGTH = 30  # Trait and specialty names


def valid_name(name: str) -> bool:
    """Determine whether a character name is valid."""
    name = " ".join(name.split())
    if len(name) > MAX_NAME_LENGTH:
        return False
    if not name:
        return False
    return bool(re.match(r"^([^\W]|[-_\s\'])+$", name))


def validate_trait_names(*traits, disciplines=False):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    # Check for duplicates (case-insensitive)
    seen = set()

    for trait in traits:
        normalized = trait.casefold()
        if normalized in seen:
            raise ValueError(f"Duplicate trait: `{trait}`.")
        seen.add(normalized)

        _check_length(trait)

        if trait.title() in RESERVED_TRAITS:
            raise ValueError(
                f"`{trait.title()}` is a reserved trait. Use `/character adjust` to set."
            )
        if trait.lower() in RESERVED_TRAITS:
            raise ValueError("Set Hunger with `/character adjust`.")
        if trait.lower() in ("powerbonus", "power_bonus"):
            raise ValueError("Power bonus is automatic if you roll with a Discipline.")

        if VALID_TRAIT_PATTERN.match(trait) is None:
            term = "Traits" if not disciplines else "Disciplines"
            raise SyntaxError(f"{term} can only have letters and underscores. Invalid: `{trait}`.")


def validate_specialty_names(*specialties):
    """
    Validates specialty (subtrait) names.
    Raises ValueError if a specialty is invalid.
    """
    seen = set()

    for specialty in specialties:
        normalized = specialty.casefold()
        if normalized in seen:
            raise ValueError(f"Duplicate specialty: {specialty}")
        seen.add(normalized)

        _check_length(specialty)

        if not specialty:
            raise ValueError("Specialty name cannot be empty.")

        if VALID_TRAIT_PATTERN.match(specialty) is None:
            raise SyntaxError(
                f"Specialties can only have letters and underscores. Invalid: `{specialty}`."
            )


def _check_length(name: str):
    """Raise a ValueError if a trait or specialty name is too long."""
    if (excess := len(name) - MAX_TRAIT_LENGTH) > 0:
        raise ValueError(f"`{name}` is too long by {pluralize(excess, 'character')}.")


def validate_tracker(track: str) -> str:
    """Validate a Health or Willpower track, returning it sorted: undamaged,
    then Superficial, then Aggravated. Raises ValueError if any box isn't a
    Damage value."""
    if invalid := set(track) - set(Damage):
        boxes = ", ".join(f"`{box}`" for box in sorted(invalid))
        raise ValueError(f"Invalid tracker boxes: {boxes}.")

    order = (Damage.NONE, Damage.SUPERFICIAL, Damage.AGGRAVATED)
    return "".join(damage * track.count(damage) for damage in order)
