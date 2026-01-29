"""Tests for interface/characters.py helper functions."""

import pytest

from interface.characters import _check_number


# Test None handling


def test_check_number_none_returns_false():
    """Test that None returns False."""
    assert _check_number("test", None) is False


# Test valid integers


def test_check_number_valid_positive():
    """Test valid positive integer strings."""
    assert _check_number("value", "5") is True
    assert _check_number("value", "100") is True
    assert _check_number("value", "0") is True


def test_check_number_valid_negative():
    """Test valid negative integer strings."""
    assert _check_number("value", "-5") is True
    assert _check_number("value", "-100") is True


# Test with +/- prefix (key feature)


def test_check_number_plus_prefix():
    """Test that +N is recognized as valid."""
    assert _check_number("value", "+5") is True
    assert _check_number("value", "+10") is True


def test_check_number_minus_prefix():
    """Test that -N is recognized as valid."""
    assert _check_number("value", "-5") is True
    assert _check_number("value", "-10") is True


# Test invalid inputs that should raise ValueError


def test_check_number_invalid_string_raises():
    """Test that non-numeric strings raise ValueError."""
    with pytest.raises(ValueError, match="`test` must be a number"):
        _check_number("test", "abc")


def test_check_number_empty_string_raises():
    """Test that empty string raises ValueError."""
    with pytest.raises(ValueError, match="`label` must be a number"):
        _check_number("label", "")


def test_check_number_float_string_raises():
    """Test that float strings raise ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "5.5")


def test_check_number_mixed_string_raises():
    """Test that strings with letters and numbers raise ValueError."""
    with pytest.raises(ValueError, match="`hp` must be a number"):
        _check_number("hp", "5abc")

    with pytest.raises(ValueError, match="`hp` must be a number"):
        _check_number("hp", "abc5")


def test_check_number_whitespace_raises():
    """Test that whitespace-only strings raise ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "   ")


def test_check_number_special_chars_raises():
    """Test that special characters raise ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "5!")

    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "#5")


# Test error message includes label


def test_check_number_error_includes_label():
    """Test that error message includes the provided label."""
    with pytest.raises(ValueError, match="`custom_label`"):
        _check_number("custom_label", "invalid")

    with pytest.raises(ValueError, match="`another_name`"):
        _check_number("another_name", "bad")


# Test edge cases


def test_check_number_leading_zeros():
    """Test numbers with leading zeros."""
    assert _check_number("value", "007") is True
    assert _check_number("value", "+007") is True


def test_check_number_just_sign_raises():
    """Test that just a sign without digits raises ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "+")

    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "-")


def test_check_number_multiple_signs_raises():
    """Test that multiple signs raise ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "++5")

    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "--5")

    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "+-5")


def test_check_number_sign_in_middle_raises():
    """Test that sign in middle of number raises ValueError."""
    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "5+5")

    with pytest.raises(ValueError, match="`value` must be a number"):
        _check_number("value", "5-3")
