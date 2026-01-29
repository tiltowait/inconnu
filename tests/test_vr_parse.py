"""Tests for VR parse utility functions."""

import pytest

from inconnu.vr.parse import needs_character
from inconnu.vr.rollparser import RollParser
from models.vchardocs import VCharTrait

# needs_character tests


def test_needs_character_empty_string():
    """Test that empty string doesn't need character."""
    assert not needs_character("")


def test_needs_character_pure_numbers():
    """Test that pure numeric syntax doesn't need character."""
    assert not needs_character("7 3 2")


def test_needs_character_with_spaces():
    """Test that numbers with various spacing don't need character."""
    assert not needs_character("  7  3  2  ")


def test_needs_character_single_number():
    """Test that a single number doesn't need character."""
    assert not needs_character("5")


def test_needs_character_math_operations():
    """Test that math operations with only numbers don't need character."""
    assert not needs_character("5 + 2 - 1")


def test_needs_character_single_letter():
    """Test that any letter requires character."""
    assert needs_character("a")


def test_needs_character_trait_name():
    """Test that trait names require character."""
    assert needs_character("strength")


def test_needs_character_multiple_traits():
    """Test that multiple trait names require character."""
    assert needs_character("strength dexterity")


def test_needs_character_trait_with_plus():
    """Test that trait addition requires character."""
    assert needs_character("strength + brawl")


def test_needs_character_trait_with_numbers():
    """Test that trait with numbers requires character."""
    assert needs_character("strength 3 2")


def test_needs_character_underscore():
    """Test that underscores require character (custom traits)."""
    assert needs_character("my_custom_trait")


def test_needs_character_specialty_delimiter():
    """Test that specialty delimiter requires character."""
    delimiter = VCharTrait.DELIMITER
    assert needs_character(f"brawl{delimiter}kindred")


def test_needs_character_mixed_case():
    """Test that mixed case letters require character."""
    assert needs_character("Strength")


def test_needs_character_only_spaces():
    """Test that only spaces doesn't need character."""
    assert not needs_character("     ")


def test_needs_character_complex_trait_syntax():
    """Test complex trait-based syntax."""
    assert needs_character("strength + dexterity + 2 - 1 3 2")


def test_needs_character_zero_pool():
    """Test that zero pool doesn't need character."""
    assert not needs_character("0 0 2")


@pytest.mark.parametrize(
    "syntax",
    [
        "str",
        "dex",
        "sta",
        "cha",
        "man",
        "com",
        "int",
        "wits",
        "res",
        "athletics",
        "brawl",
        "craft",
        "drive",
        "firearms",
        "melee",
        "larceny",
        "stealth",
        "survival",
        "dominate",
        "animalism",
        "auspex",
    ],
)
def test_common_traits_need_character(syntax):
    """Test that common trait abbreviations need character."""
    assert needs_character(syntax)


@pytest.mark.parametrize(
    "syntax",
    [
        "0",
        "1",
        "10",
        "99",
        "0 0 0",
        "10 5 3",
        "1 2 3",
    ],
)
def test_pure_numbers_dont_need_character(syntax):
    """Test various numeric syntaxes don't need character."""
    assert not needs_character(syntax)


# Syntax validation tests


def test_invalid_character_multiplication():
    """Test that multiplication is detected as invalid."""
    assert RollParser.has_invalid_characters("strength * 2")


def test_invalid_character_comma():
    """Test that comma is detected as invalid."""
    assert RollParser.has_invalid_characters("dex,str")


def test_invalid_character_parentheses():
    """Test that parentheses are detected as invalid."""
    assert RollParser.has_invalid_characters("brawl (kindred)")


def test_valid_characters_trait_addition():
    """Test that trait addition is valid."""
    assert not RollParser.has_invalid_characters("strength + brawl")


def test_valid_characters_trait_with_params():
    """Test that trait with parameters is valid."""
    assert not RollParser.has_invalid_characters("strength 3 2")


def test_valid_characters_pure_numbers():
    """Test that pure numbers are valid."""
    assert not RollParser.has_invalid_characters("7 3 2")


def test_valid_characters_specialty_delimiter():
    """Test that specialty delimiter is valid."""
    assert not RollParser.has_invalid_characters("brawl.kindred")


def test_possible_spec_use_parentheses():
    """Test detection of parentheses suggesting specialty syntax error."""
    assert RollParser.possible_spec_use("brawl (kindred)")


def test_possible_spec_use_with_params():
    """Test detection of specialty error with parameters."""
    assert RollParser.possible_spec_use("firearms (pistols) 3 2")


def test_not_possible_spec_use_addition():
    """Test that normal trait addition isn't flagged."""
    assert not RollParser.possible_spec_use("strength + brawl")


def test_not_possible_spec_use_correct_specialty():
    """Test that correct specialty syntax isn't flagged."""
    assert not RollParser.possible_spec_use("brawl.kindred")


def test_not_possible_spec_use_numbers():
    """Test that pure numbers aren't flagged."""
    assert not RollParser.possible_spec_use("7 3 2")


# Comment parsing tests


def test_comment_split_basic():
    """Test that comments are split from syntax."""
    syntax = "strength + brawl 3 2 # attacking the lupine"
    parts = syntax.split("#", 1)

    assert len(parts) == 2
    assert parts[0].strip() == "strength + brawl 3 2"
    assert parts[1].strip() == "attacking the lupine"


def test_comment_split_multiple_hashes():
    """Test that only first hash is used as delimiter."""
    syntax = "str 3 2 # comment with # another hash"
    parts = syntax.split("#", 1)

    assert len(parts) == 2
    assert parts[1] == " comment with # another hash"


def test_comment_split_no_comment():
    """Test syntax without comment."""
    syntax = "strength 3 2"
    parts = syntax.split("#", 1)

    assert len(parts) == 1


def test_comment_split_empty_comment():
    """Test syntax with empty comment."""
    syntax = "strength 3 2 #"
    parts = syntax.split("#", 1)

    assert len(parts) == 2
    assert parts[1] == ""


def test_comment_split_hash_in_comment():
    """Test hash symbols within the comment itself."""
    syntax = "str # #hashtag #blessed"
    parts = syntax.split("#", 1)

    assert parts[1].strip() == "#hashtag #blessed"
