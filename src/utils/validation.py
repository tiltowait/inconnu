"""Validation utilities for character data."""

import re

from constants import RESERVED_TRAITS, Damage, name_key
from utils.text import pluralize

# Words separated by single spaces. Linear, unlike ([A-Za-z_]+ ?)+, which
# backtracks exponentially on a near miss. Words may have apostrophes
# (O'Brien, Dogs', 'Til), but need a letter or underscore
_TRAIT_WORD = r"'*[A-Za-z_][A-Za-z_']*"
VALID_TRAIT_PATTERN = re.compile(rf"^{_TRAIT_WORD}(?: {_TRAIT_WORD})*$")
VALID_NAME_PATTERN = re.compile(r"^[\w\s'-]+$")
MAX_NAME_LENGTH = 30  # Character names
MAX_TRAIT_LENGTH = 40  # Trait and specialty names


def reads_as_hunger(word: str) -> bool:
    """Whether the roll parser reads a word as Hunger: current_hunger, or
    hunger or a prefix of it."""
    word = word.lower()
    return word == "current_hunger" or (bool(word) and "hunger".startswith(word))


def valid_name(name: str) -> bool:
    """Determine whether a character name is valid."""
    name = " ".join(name.split())
    if len(name) > MAX_NAME_LENGTH:
        return False
    if not name:
        return False
    return VALID_NAME_PATTERN.match(name) is not None


def validate_trait_names(*traits: str, disciplines=False):
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
        if trait.lower() in ("powerbonus", "power_bonus", "power bonus"):
            raise ValueError("Power bonus is automatic if you roll with a Discipline.")

        term = "Traits" if not disciplines else "Disciplines"
        _check_words(trait, term)


def validate_specialty_names(*specialties: str):
    """
    Validates specialty (subtrait) names.
    Raises ValueError if a specialty is invalid.
    """
    seen = set()

    for specialty in specialties:
        normalized = name_key(specialty)  # "BigCats" duplicates Big Cats
        if normalized in seen:
            raise ValueError(f"Duplicate specialty: {specialty}")
        seen.add(normalized)

        _check_length(specialty)

        if not specialty:
            raise ValueError("Specialty name cannot be empty.")

        _check_words(specialty, "Specialties")


def _check_words(name: str, term: str):
    """Raise a SyntaxError if a trait or specialty name has invalid
    characters, or if a word after its first reads as Hunger. In a roll, a
    word after a trait starts the Hunger stack if it reads as Hunger, so such
    a name couldn't be rolled. (A specialty's first word follows a dot, so
    it's safe.)"""
    if VALID_TRAIT_PATTERN.match(name) is None:
        raise SyntaxError(
            f"{term} can only have letters, underscores, and apostrophes, with single spaces "
            f"between words. Invalid: `{name}`."
        )
    for word in name.split()[1:]:
        if reads_as_hunger(word):
            raise SyntaxError(
                f"`{name}` can't have `{word}` after its first word, since rolls read it as Hunger."
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
