"""Test the roll syntax parser."""

import pytest

import errors
from inconnu.vr.parse import needs_character
from inconnu.vr.rollparser import RollParser
from models.vchar import VChar
from tests.characters import gen_char


@pytest.fixture
def character() -> VChar:
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 4, "Oblivion": 5, "Resolve": 4})
    char.add_specialties("Brawl", ["Kindred"])
    char.add_powers("Oblivion", "ShadowCloak")
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
        ("stren+br.kin", "Strength + Brawl (Kindred)", 8),
        ("stren + br+obl", "Strength + Brawl + Oblivion", 12),
        ("stren + .shadow", "Strength + Oblivion (ShadowCloak)", 8),
    ],
)
def test_pool_creation(syntax: str, pool_str: str, value: int, character: VChar):
    p = RollParser(character, syntax)
    assert p.pool_str == pool_str
    assert p.pool == value


def test_solo_semicolon():
    char = gen_char("vampire")
    char.assign_traits({"Brawl": 1})
    char.add_specialties("Brawl", ["Kindred"])

    _ = RollParser(char, ".")

    char.add_specialties("Brawl", ["Kine"])
    with pytest.raises(errors.AmbiguousTraitError):
        _ = RollParser(char, ".")


@pytest.mark.parametrize(
    "syntax,stack,expand_only",
    [
        ("stren+br.kin", ["Strength", "+", "Brawl.Kindred"], True),
        ("stren+br.kin", ["Strength", "+", "Brawl (Kindred)"], False),
    ],
)
def test_stack_expansion(syntax: str, stack: str, expand_only: bool, character: VChar):
    p = RollParser(character, syntax, expand_only)
    assert p.pool_stack == stack


@pytest.mark.parametrize(
    "syntax,should_fail",
    [
        ("stren+br", False),
        ("1+2", False),
        ("strength + brawl hunger", False),
        ("strength + brawl current_hunger", False),
        ("stren+hung", True),
        ("strength + hunger", True),
        ("strength + brawl + current_hunger", True),
    ],
)
def test_hunger_in_pool(syntax: str, should_fail: bool, character: VChar):
    if should_fail:
        with pytest.raises(errors.HungerInPool):
            _ = RollParser(character, syntax)
    else:
        try:
            _ = RollParser(character, syntax)
        except errors.HungerInPool:
            pytest.fail("Should not have raised HungerInPool")


@pytest.mark.parametrize(
    "syntax,bp,pool,dice",
    [
        ("res+obl", 1, "Resolve + Oblivion", 9),
        ("res+obl", 2, "Resolve + Oblivion + PowerBonus", 10),
        ("res+obl", 3, "Resolve + Oblivion + PowerBonus", 10),
        ("res+obl", 4, "Resolve + Oblivion + PowerBonus", 11),
        ("res+obl", 5, "Resolve + Oblivion + PowerBonus", 11),
        ("res+obl", 6, "Resolve + Oblivion + PowerBonus", 12),
        ("res+obl", 7, "Resolve + Oblivion + PowerBonus", 12),
        ("res+obl", 8, "Resolve + Oblivion + PowerBonus", 13),
        ("res+obl", 9, "Resolve + Oblivion + PowerBonus", 13),
        ("res+obl", 10, "Resolve + Oblivion + PowerBonus", 14),
        ("stren+br", 10, "Strength + Brawl", 7),  # No power bonus on non-Disciplines
    ],
)
def test_auto_blood_potency(syntax: str, bp: int, pool: str, dice: int, character: VChar):
    character.potency = bp
    p = RollParser(character, syntax)
    assert p.pool_str == pool
    assert p.pool == dice


@pytest.mark.parametrize(
    "syntax,expected_str,expected_dice,add_bonus",
    [
        ("Resolve + Oblivion", "Resolve + Oblivion + PowerBonus", 10, True),
        ("Resolve + Oblivion", "Resolve + Oblivion", 9, False),
        ("Strength + Brawl", "Strength + Brawl", 7, True),
        ("Strength + Brawl", "Strength + Brawl", 7, False),
    ],
)
def test_no_power_bonus(
    syntax: str,
    expected_str: str,
    expected_dice: int,
    add_bonus: bool,
    character: VChar,
):
    character.potency = 2
    p = RollParser(character, syntax, power_bonus=add_bonus)
    assert p.pool_str == expected_str
    assert p.pool == expected_dice


@pytest.mark.parametrize(
    "syntax,needs",
    [
        ("3", False),
        ("3 + 2", False),
        ("3 4 5", False),
        ("Strength", True),
        ("3 + Strength", True),
        ("Strength + Brawl hunger 3", True),
        ("ü", True),
        ("3 + .", True),
        ("3 + _", True),
    ],
)
def test_needs_character(syntax: str, needs: bool):
    assert needs_character(syntax) == needs
