"""Tests for utils/validation.py."""

import pytest

from utils.validation import validate_tracker


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
