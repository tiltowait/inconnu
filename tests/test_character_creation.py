"""Tests for character creation validation."""

import pytest

from inconnu.character import valid_name

# Character name validation tests


@pytest.mark.parametrize(
    "name",
    [
        "John",
        "Jane Doe",
        "Mary-Ann",
        "Jean_Paul",
        "O'Brien",
        "Two Words",
        "Three Word Name",
        "Hyphen-ated",
        "Under_score",
        "Mixed-Name_Style",
        "D'Angelo",
        "Multi-Part_Name O'Test",
        "Name123",
        "Agent007",
    ],
)
def test_valid_character_names(name):
    """Test that valid character names pass validation."""
    assert valid_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "Test@Character",
        "With#Hash",
        "With$Dollar",
        "Percent%",
        "With.Period",
        "With!Exclamation",
        "Question?",
        "Ampersand&",
        "Asterisk*",
        "Plus+",
        "Equals=",
        "Brackets[]",
        "Parens()",
        "Braces{}",
    ],
)
def test_invalid_character_names(name):
    """Test that invalid character names fail validation."""
    assert not valid_name(name)


def test_valid_name_empty_string():
    """Test that empty string is invalid."""
    assert not valid_name("")


def test_valid_name_only_spaces():
    """Test that only spaces is invalid."""
    assert not valid_name("   ")


def test_valid_name_single_letter():
    """Test that single letter is valid."""
    assert valid_name("A")


def test_valid_name_unicode():
    """Test behavior with unicode characters."""
    # The regex should allow unicode letters
    assert valid_name("François")
    assert valid_name("José")
