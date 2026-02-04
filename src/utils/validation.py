"""Validation utilities for character data."""

import re

from constants import RESERVED_TRAITS

VALID_TRAIT_PATTERN = re.compile(r"^[A-Za-z_]+$")


def valid_name(name: str) -> bool:
    """Determine whether a character name is valid."""
    name = " ".join(name.split())
    if len(name) > 30:
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

        if (trait_len := len(trait)) > 20:
            raise ValueError(f"`{trait}` is too long by {trait_len - 20} characters.")

        if trait.title() in RESERVED_TRAITS:
            raise ValueError(
                f"`{trait.title()}` is a reserved trait. Use `/character adjust` to set."
            )
        if trait.lower() in RESERVED_TRAITS:
            raise ValueError("Set Hunger with `/character adjust`.")
        if trait.lower() in ["powerbonus", "power_bonus"]:
            raise ValueError("Power bonus is automatic if you roll with a Discipline.")

        if VALID_TRAIT_PATTERN.match(trait) is None:
            term = "Traits" if not disciplines else "Disciplines"
            raise SyntaxError(f"{term} can only have letters and underscores. Invalid: `{trait}`.")


def validate_specialty_names(*specialties):
    """
    Validates specialty (subtrait) names.
    Raises ValueError if a specialty is invalid.
    """
    for specialty in specialties:
        if (spec_len := len(specialty)) > 20:
            raise ValueError(f"`{specialty}` is too long by {spec_len - 20} characters.")

        if not specialty:
            raise ValueError("Specialty name cannot be empty.")

        if VALID_TRAIT_PATTERN.match(specialty) is None:
            raise SyntaxError(
                f"Specialties can only have letters and underscores. Invalid: `{specialty}`."
            )
