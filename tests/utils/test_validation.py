"""Tests for utils/validation.py."""

from collections.abc import Callable

import pytest

from utils.validation import (
    MAX_TRAIT_LENGTH,
    validate_specialty_names,
    validate_tracker,
    validate_trait_names,
)

type NameValidator = Callable[..., None]


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
