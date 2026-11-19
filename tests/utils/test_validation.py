"""Tests for utils/validation.py."""

from collections.abc import Callable

import pytest

from utils.validation import (
    MAX_TRAIT_LENGTH,
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
