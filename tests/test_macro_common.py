"""Tests for macro common utilities."""

import pytest

from inconnu.macros import macro_common


# Macro name validation tests


def test_valid_macro_name_letters():
    """Test that letter-only names are valid."""
    assert macro_common.is_macro_name_valid("attack")


def test_valid_macro_name_with_underscore():
    """Test that names with underscores are valid."""
    assert macro_common.is_macro_name_valid("melee_attack")


def test_valid_macro_name_uppercase():
    """Test that uppercase names are valid."""
    assert macro_common.is_macro_name_valid("ATTACK")


def test_valid_macro_name_mixed_case():
    """Test that mixed case names are valid."""
    assert macro_common.is_macro_name_valid("MyAttack")


def test_valid_macro_name_multiple_underscores():
    """Test that multiple underscores are valid."""
    assert macro_common.is_macro_name_valid("my_special_attack")


def test_invalid_macro_name_numbers():
    """Test that names with numbers are invalid."""
    assert not macro_common.is_macro_name_valid("attack2")


def test_invalid_macro_name_special_chars():
    """Test that names with special characters are invalid."""
    assert not macro_common.is_macro_name_valid("attack-combo")


def test_invalid_macro_name_spaces():
    """Test that names with spaces are invalid."""
    assert not macro_common.is_macro_name_valid("my attack")


def test_invalid_macro_name_hyphen():
    """Test that hyphens are invalid."""
    assert not macro_common.is_macro_name_valid("multi-word")


def test_invalid_macro_name_period():
    """Test that periods are invalid."""
    assert not macro_common.is_macro_name_valid("macro.name")


def test_invalid_macro_name_starting_with_number():
    """Test that names starting with numbers are invalid."""
    assert not macro_common.is_macro_name_valid("1attack")


def test_invalid_macro_name_empty():
    """Test that empty strings are invalid."""
    assert not macro_common.is_macro_name_valid("")


def test_invalid_macro_name_only_underscore():
    """Test that only underscores are invalid."""
    assert not macro_common.is_macro_name_valid("_")


def test_valid_macro_name_single_letter():
    """Test that single letter is valid."""
    assert macro_common.is_macro_name_valid("a")


@pytest.mark.parametrize(
    "name",
    [
        "attack",
        "defend",
        "SHOUT",
        "blood_surge",
        "dominate_gaze",
        "AwesomePower",
    ],
)
def test_valid_macro_names_parametrized(name):
    """Test various valid macro names."""
    assert macro_common.is_macro_name_valid(name)


@pytest.mark.parametrize(
    "name",
    [
        "attack123",
        "my-attack",
        "my attack",
        "attack!",
        "@attack",
        "attack.power",
        "123",
        "",
    ],
)
def test_invalid_macro_names_parametrized(name):
    """Test various invalid macro names."""
    assert not macro_common.is_macro_name_valid(name)
