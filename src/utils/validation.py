"""Validation utilities for character data."""

import re

from constants import RESERVED_TRAITS, Damage, name_key
from utils.text import pluralize, straighten_apostrophes

# Words separated by single spaces. Linear, unlike ([A-Za-z_]+ ?)+, which
# backtracks exponentially on a near miss. Words may have apostrophes
# (O'Brien, Dogs', 'Til), but need a letter or underscore
_TRAIT_WORD = r"'*[A-Za-z_][A-Za-z_']*"
VALID_TRAIT_PATTERN = re.compile(rf"^{_TRAIT_WORD}(?: {_TRAIT_WORD})*$")
# Names are checked with whitespace collapsed, so a space is the only
# whitespace left. Python's \w is exactly [\p{L}\p{N}_], so the JS form (for
# the web app; needs the u flag) matches the same names, given the same
# Unicode version. Characters newer than one side's version may differ
VALID_NAME_PATTERN = re.compile(r"^[\w '-]+$")
VALID_NAME_PATTERN_JS = r"^[\p{L}\p{N}_ '-]+$"
MAX_NAME_LENGTH = 30  # Character names
MAX_TRAIT_LENGTH = 40  # Trait and specialty names
# Rolls read a word as Hunger if it's an alias or a prefix of HUNGER_WORD
HUNGER_WORD = "hunger"
HUNGER_ALIASES = ("current_hunger",)
# Reserved trait names, compared by name_key()
RESERVED_TRAIT_KEYS = {name_key(trait): trait for trait in RESERVED_TRAITS}
POWER_BONUS_KEYS = ("powerbonus", "power_bonus")
MAX_MACRO_NAME_LENGTH = 50
MAX_MACRO_COMMENT_LENGTH = 300
MAX_MACRO_ROUSES = 5
MAX_MACRO_DIFFICULTY = 100  # For web edits; Discord has no limit
MAX_MACRO_POOL_TOKENS = 50  # Traits, numbers, and operators, for web edits
# Letters and underscores, with at least one letter. Served to the web app, so
# it must also be a valid JS pattern
VALID_MACRO_NAME_PATTERN = re.compile(r"^_*[A-Za-z][A-Za-z_]*$")
# "no" comes from /macro update; "show", from /macro create
MACRO_STAINING = ("apply", "show", "no")


def clean_name(name: str) -> str:
    """A character, trait, or specialty name with its whitespace collapsed and
    curly apostrophes, which phones type, straightened. Names are checked and
    stored in this form."""
    return " ".join(straighten_apostrophes(name).split())


def reads_as_hunger(word: str) -> bool:
    """Whether the roll parser reads a word as Hunger: current_hunger, or
    hunger or a prefix of it."""
    word = word.lower()
    return word in HUNGER_ALIASES or (bool(word) and HUNGER_WORD.startswith(word))


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
    seen: set[str] = set()

    for trait in traits:
        normalized = name_key(trait)  # "NightDriving" duplicates Night Driving
        if normalized in seen:
            raise ValueError(f"Duplicate trait: `{trait}`.")
        seen.add(normalized)

        _check_length(trait)

        if normalized in HUNGER_ALIASES:
            raise ValueError("Set Hunger with `/character adjust`.")
        if (reserved := RESERVED_TRAIT_KEYS.get(normalized)) is not None:
            raise ValueError(f"`{reserved}` is a reserved trait. Use `/character adjust` to set.")
        if normalized in POWER_BONUS_KEYS:
            raise ValueError("Power bonus is automatic if you roll with a Discipline.")

        term = "Traits" if not disciplines else "Disciplines"
        _check_words(trait, term)


def validate_specialty_names(*specialties: str):
    """
    Validates specialty (subtrait) names.
    Raises ValueError if a specialty is invalid.
    """
    seen: set[str] = set()

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
