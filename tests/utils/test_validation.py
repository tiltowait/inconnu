"""Tests for utils/validation.py."""

import sys
import unicodedata
from collections.abc import Callable

import pytest

from utils.validation import (
    MAX_TRAIT_LENGTH,
    VALID_NAME_PATTERN,
    VALID_NAME_PATTERN_JS,
    clean_name,
    reads_as_hunger,
    validate_specialty_names,
    validate_tracker,
    validate_trait_names,
)

type NameValidator = Callable[..., None]

NAME_VALIDATORS = [validate_trait_names, validate_specialty_names]


@pytest.mark.parametrize(
    "word,expected",
    [
        ("h", True),
        ("Hun", True),
        ("HUNGER", True),
        ("current_hunger", True),
        ("", False),
        ("hungry", False),
        ("hunters", False),
        ("hungers", False),
        ("current", False),
    ],
)
def test_reads_as_hunger(word: str, expected: bool):
    """Only hunger, its prefixes, and current_hunger read as Hunger."""
    assert reads_as_hunger(word) is expected


@pytest.mark.parametrize("validator", NAME_VALIDATORS)
@pytest.mark.parametrize(
    "name",
    [
        "Brawl",
        "Animal Ken",
        "big cats",
        "Foo_Bar Baz",
        "A B C",
        "Hunger Pangs",
        "Bloodhound",
        "Beast's Fang",
        "O'Brien",
        "Dogs'",
        "'Til Death",
        "Rock'n'Roll",
    ],
)
def test_valid_names(validator: NameValidator, name: str):
    """Words of letters, underscores, and apostrophes, separated by single
    spaces, are valid. Hunger may be the first word."""
    validator(name)


@pytest.mark.parametrize("validator", NAME_VALIDATORS)
@pytest.mark.parametrize(
    "name",
    [
        "Animal  Ken",
        " Brawl",
        "Brawl ",
        "Animal\tKen",
        "Big-Cats",
        "Brawl2",
        "A.B",
        "'",
        "Dog ' Fang",
        "O’Brien",  # Input parsers straighten curly apostrophes first
    ],
)
def test_invalid_characters(validator: NameValidator, name: str):
    """Anything but single spaces between words of letters, underscores, and
    apostrophes is rejected. A word needs a letter or underscore."""
    with pytest.raises(SyntaxError, match="letters, underscores, and apostrophes"):
        validator(name)


@pytest.mark.parametrize("validator", NAME_VALIDATORS)
@pytest.mark.parametrize(
    "name,word",
    [
        ("Ravenous Hunger", "Hunger"),
        ("Animal H", "H"),
        ("Foo hu Bar", "hu"),
        ("Foo current_hunger", "current_hunger"),
    ],
)
def test_hunger_after_first_word(validator: NameValidator, name: str, word: str):
    """A later word that reads as Hunger is rejected, since a roll would
    start the Hunger stack there."""
    with pytest.raises(SyntaxError, match=f"`{word}` after its first word"):
        validator(name)


@pytest.mark.parametrize("name", ["Willpower", "will power", "POTENCY", "Hu Manity"])
def test_reserved_traits_however_spaced(name: str):
    """Reserved traits are compared by name key, ignoring case and spaces."""
    with pytest.raises(ValueError, match="is a reserved trait"):
        validate_trait_names(name)


def test_current_hunger_reserved():
    """current_hunger points the player to /character adjust."""
    with pytest.raises(ValueError, match="Set Hunger"):
        validate_trait_names("Current_Hunger")


def test_power_bonus_with_space_reserved():
    """Power Bonus is reserved however it's spaced."""
    with pytest.raises(ValueError, match="Power bonus is automatic"):
        validate_trait_names("Power Bonus")


@pytest.mark.parametrize(
    "track,expected",
    [
        ("", ""),
        ("....", "...."),
        ("x/.", "./x"),
        ("/x./x.", "..//xx"),
        ("xxx", "xxx"),
    ],
)
def test_validate_tracker_sorts(track: str, expected: str):
    """Valid tracks are sorted undamaged, Superficial, Aggravated."""
    assert validate_tracker(track) == expected


@pytest.mark.parametrize("track", ["..o", "X..", ".. /", "5"])
def test_validate_tracker_rejects_invalid_boxes(track: str):
    """Any box that isn't a Damage value is rejected."""
    with pytest.raises(ValueError, match="Invalid tracker boxes"):
        validate_tracker(track)


def test_validate_tracker_lists_each_invalid_box():
    """The error names each invalid box once."""
    with pytest.raises(ValueError) as exc_info:
        validate_tracker("ab.a")
    assert str(exc_info.value) == "Invalid tracker boxes: `a`, `b`."


@pytest.mark.parametrize("validator", [validate_trait_names, validate_specialty_names])
def test_name_length_limit(validator: NameValidator):
    """Trait and specialty names may be exactly the maximum length."""
    validator("A" * MAX_TRAIT_LENGTH)


@pytest.mark.parametrize(
    "validator,excess,message",
    [
        (validate_trait_names, 1, "too long by 1 character."),
        (validate_specialty_names, 1, "too long by 1 character."),
        (validate_trait_names, 2, "too long by 2 characters."),
        (validate_specialty_names, 2, "too long by 2 characters."),
    ],
)
def test_name_too_long(validator: NameValidator, excess: int, message: str):
    """Names over the maximum are rejected, with the excess pluralized."""
    with pytest.raises(ValueError) as exc_info:
        validator("A" * (MAX_TRAIT_LENGTH + excess))
    assert str(exc_info.value).endswith(message)


def test_duplicate_specialties_ignore_spaces():
    """Specialties differing only in case or spaces are duplicates."""
    with pytest.raises(ValueError, match="Duplicate specialty: BigCats"):
        validate_specialty_names("Big Cats", "BigCats")


def test_duplicate_traits_ignore_spaces():
    """Traits differing only in case or spaces are duplicates."""
    with pytest.raises(ValueError, match="Duplicate trait: `NightDriving`"):
        validate_trait_names("Night Driving", "NightDriving")


def js_name_char(char: str) -> bool:
    """Whether VALID_NAME_PATTERN_JS's class, [\\p{L}\\p{N}_ '-], takes a
    character, emulated with Unicode categories."""
    return char in "_ '-" or unicodedata.category(char)[0] in "LN"


def test_js_name_pattern_is_emulated():
    """The emulation below is of the pattern actually served."""
    assert VALID_NAME_PATTERN_JS == r"^[\p{L}\p{N}_ '-]+$"


def test_name_patterns_agree_on_every_character():
    """The Python and JS name patterns take exactly the same characters, so
    the web app accepts the names the bot does."""
    disagreements = [
        hex(code)
        for code in range(sys.maxunicode + 1)
        if (VALID_NAME_PATTERN.match(chr(code)) is not None) != js_name_char(chr(code))
    ]
    assert disagreements == []


@pytest.mark.parametrize(
    "name,expected",
    [
        ("  Animal   Ken ", "Animal Ken"),
        ("Dogs\u2019", "Dogs'"),
        ("\u2018Til\tDawn", "'Til Dawn"),
        ("O'Brien", "O'Brien"),
    ],
)
def test_clean_name(name: str, expected: str):
    """Whitespace collapses and curly apostrophes straighten."""
    assert clean_name(name) == expected
