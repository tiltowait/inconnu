"""Test the roll syntax parser."""

import pytest

from inconnu.models.vchar import VChar
from inconnu.vr.rollparser import RollParser
from tests.characters import gen_char


@pytest.fixture
def character() -> VChar:
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 4, "Oblivion": 5, "Resolve": 4})
    char.add_specialties("Brawl", ["Kindred"])
    return char


@pytest.mark.parametrize(
    "string,should_fail",
    [
        ("123+apples", False),
        ("strength + brawl + kindred_only", False),
        ("strength - 1", False),
        ("strength * 3", True),
        (",", True),
    ],
)
def test_has_invalid_characters(string: str, should_fail: bool):
    assert RollParser.has_invalid_characters(string) == should_fail


@pytest.mark.parametrize(
    "syntax,pool_str,value",
    [
        ("stren+br", "Strength + Brawl", 7),
        ("stren+br hunger", "Strength + Brawl", 7),
        ("stren+br:kin", "Strength + Brawl (Kindred)", 8),
        ("stren + br+obl", "Strength + Brawl + Oblivion", 12),
    ],
)
def test_pool_creation(syntax: str, pool_str: str, value: int, character: VChar):
    p = RollParser(character, syntax)
    assert p.pool_str == pool_str
    assert p.pool == value


@pytest.mark.parametrize(
    "syntax,stack,expand_only",
    [
        ("stren+br:kin", ["Strength", "+", "Brawl:Kindred"], True),
        ("stren+br:kin", ["Strength", "+", "Brawl (Kindred)"], False),
    ],
)
def test_stack_expansion(syntax: str, stack: str, expand_only: bool, character: VChar):
    p = RollParser(character, syntax, expand_only)
    assert p.pool_stack == stack
