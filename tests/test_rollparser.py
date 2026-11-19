"""Test the roll syntax parser."""

from unittest.mock import patch

import pytest

import errors
from inconnu.vr.parse import needs_character
from inconnu.vr.rollparser import MAX_SPLIT_WORDS, RollParser, eval_expr
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
        ("wits + beast's fang", False),
        ("wits + beast\u2019s fang", False),  # Phones type curly apostrophes
        ('wits + "fang"', True),
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


@pytest.mark.parametrize(
    "syntax,tokens",
    [
        ("", []),
        ("stren+br", ["stren", "+", "br"]),
        ("strength + brawl hunger 3", ["strength", "+", "brawl", "hunger", "3"]),
        ("br . kin", ["br.kin"]),
        ("br. kin+obl .shadow", ["br.kin", "+", "obl.shadow"]),
        (".shadow", [".shadow"]),
        (".", ["."]),
        ("br.", ["br."]),
        ("br.. kin", ["br..kin"]),
        (". . shadow", ["..shadow"]),
        ("3 +- 2", ["3", "+", "-", "2"]),
        ("  7\t3 2  ", ["7", "3", "2"]),
        ("ü", ["ü"]),
    ],
)
def test_tokenize(syntax: str, tokens: list[str]):
    """Operators split operands, and whitespace around delimiters is ignored."""
    assert RollParser.tokenize(syntax) == tokens


@pytest.mark.parametrize("syntax", ["strength * 3", "brawl (kindred)", ","])
def test_tokenize_invalid(syntax: str, character: VChar):
    """Invalid characters raise SyntaxError, whether tokenizing or parsing."""
    with pytest.raises(SyntaxError):
        RollParser.tokenize(syntax)
    with pytest.raises(SyntaxError):
        RollParser(character, syntax)


@pytest.mark.parametrize(
    "syntax,should_match",
    [
        ("brawl (kindred)", True),
        ("brawl(kindred) + str", True),
        ("brawl.kindred", False),
        ("brawl (kindred", False),
        ("brawl ) kindred (", False),
    ],
)
def test_possible_spec_use(syntax: str, should_match: bool):
    """Parenthesized specialties are detected so users can be hinted."""
    assert RollParser.possible_spec_use(syntax) == should_match


@pytest.mark.parametrize(
    "syntax,pool_str,pool",
    [
        ("+ stren + br", "Strength + Brawl", 7),
        ("- 1 + stren", "-1 + Strength", 2),
        ("-stren + br", "-Strength + Brawl", 1),
        ("3 + - + - 2", None, 5),
        ("7", None, 7),
    ],
)
def test_leading_operators(syntax: str, pool_str: str | None, pool: int, character: VChar):
    """Leading operators are evaluated and tidied in the pool string."""
    p = RollParser(character, syntax)
    assert p.pool_str == pool_str
    assert p.pool == pool


@pytest.mark.parametrize(
    "syntax,pool,hunger,difficulty",
    [
        ("stren+br", 7, 0, 0),
        ("stren+br 2", 7, 2, 0),
        ("stren+br 2 3", 7, 2, 3),
        ("stren+br hunger 3", 7, 2, 3),
        ("stren+br current_hunger 3", 7, 2, 3),
        ("stren+br 1+1 4-1", 7, 2, 3),
        ("stren+br hunger + 1 2", 7, 3, 2),
        ("stren+br current_hunger - 1", 7, 1, 0),
        ("7 3 2", 7, 3, 2),
    ],
)
def test_vampire_stacks(syntax: str, pool: int, hunger: int, difficulty: int, character: VChar):
    """Stacks go pool, Hunger, Difficulty, and Hunger and Difficulty may use arithmetic."""
    character.hunger = 2
    p = RollParser(character, syntax)
    assert p.pool == pool
    assert p.hunger == hunger
    assert p.difficulty == difficulty


@pytest.fixture
def mortal() -> VChar:
    """A mortal with a few traits."""
    char = gen_char("mortal")
    char.assign_traits({"Strength": 3, "Brawl": 4})
    return char


@pytest.mark.parametrize(
    "syntax,hunger,difficulty",
    [
        ("stren+br", 0, 0),
        # A placeholder 0 Hunger is dropped, so the next stack is Difficulty
        ("stren+br 0", 0, 0),
        ("stren+br 0 3", 0, 3),
        ("stren+br current_hunger 3", 0, 3),
        # Anything else in the Hunger position is the Difficulty
        ("stren+br 3", 0, 3),
    ],
)
def test_mortal_stacks(syntax: str, hunger: int, difficulty: int, mortal: VChar):
    """Mortals have no Hunger, so a Hunger value is dropped or read as Difficulty."""
    p = RollParser(mortal, syntax)
    assert p.hunger == hunger
    assert p.difficulty == difficulty


@pytest.mark.parametrize("syntax", ["stren+br 2 3", "stren+br 2 stren", "stren+br 2 finance"])
def test_mortal_nonzero_hunger_and_difficulty(syntax: str, mortal: VChar):
    """A mortal's nonzero Hunger is read as Difficulty, so a Difficulty is extra.
    Too many parameters wins over an invalid or unknown Difficulty."""
    with pytest.raises(errors.TooManyParameters):
        RollParser(mortal, syntax)


def test_mortal_hunger_keyword(mortal: VChar):
    """Mortals don't have a Hunger trait."""
    with pytest.raises(errors.TraitNotFound):
        RollParser(mortal, "stren+br hunger 3")


def test_no_character_stacks():
    """Number-only rolls don't need a character."""
    p = RollParser(None, "7 3 2")
    assert (p.pool, p.hunger, p.difficulty) == (7, 3, 2)
    assert p.pool_str is None


@pytest.mark.parametrize(
    "syntax,count,pool,hunger,difficulty,extra",
    [
        ("stren+br 1 2 3", 4, "Strength + Brawl", "1", "2", "3"),
        ("stren+br hunger 2 3 4", 5, "Strength + Brawl", "Current Hunger", "2", "3 4"),
        # Extras are shown as typed
        ("stren+br 1 2 res", 4, "Strength + Brawl", "1", "2", "res"),
        ("7 1 2 3", 4, "7", "1", "2", "3"),
    ],
)
def test_too_many_parameters(
    syntax: str,
    count: int,
    pool: str,
    hunger: str,
    difficulty: str,
    extra: str,
    character: VChar,
):
    """Extra stacks raise an error showing the interpretation and the extras."""
    with pytest.raises(errors.TooManyParameters) as exc_info:
        RollParser(character, syntax)

    message = str(exc_info.value)
    assert exc_info.value.count == count
    assert f"***Pool:*** `{pool}`" in message
    assert f"***Hunger:*** `{hunger}`" in message
    assert f"***Difficulty:*** `{difficulty}`" in message
    assert f"**Unexpected extra parameter(s):** `{extra}`" in message


@pytest.mark.parametrize("syntax", ["", "+", "stren +", "stren+br 2 +", "stren+br 2 3 -"])
def test_incomplete_expressions(syntax: str, character: VChar):
    """Dangling operators and empty syntax can't be evaluated."""
    with pytest.raises(SyntaxError, match="Invalid syntax!"):
        RollParser(character, syntax)


def test_list_input(character: VChar):
    """Macros pass a stored pool stack plus Hunger and Difficulty as a list."""
    character.hunger = 2
    p = RollParser(character, ["Strength", "+", "Brawl.Kindred", "+", 1, "current_hunger", 3])
    assert p.pool_str == "Strength + Brawl (Kindred) + 1"
    assert p.pool == 9
    assert p.hunger == 2
    assert p.difficulty == 3


@pytest.mark.parametrize(
    "expr,value",
    [
        ("7", 7),
        ("3 + 4", 7),
        ("3 - 4", -1),
        ("- 2 + + 3", 1),
        ("03", 3),
        ("00", 0),
        ("0", 0),
        ("100 - 010", 90),
    ],
)
def test_eval_expr(expr: str, value: int):
    """Addition, subtraction, and unary signs are evaluated."""
    assert eval_expr(expr) == value


def test_leading_zeros(character: VChar):
    """Numbers with leading zeros are read as plain numbers."""
    p = RollParser(character, "strength + 02 01 03")
    assert p.pool == 5
    assert p.hunger == 1
    assert p.difficulty == 3


def test_eval_expr_rejects_names():
    """Only numbers can be evaluated."""
    with pytest.raises(TypeError):
        eval_expr("strength + 1")


# Hunger and Difficulty rules
#
# Hunger is numbers, current_hunger, or a token that resolves to Hunger, with
# arithmetic. Difficulty is numbers only, with arithmetic.


@pytest.fixture
def hungry() -> VChar:
    """A Hungry vampire with the traits players most often misroll."""
    char = gen_char("vampire")
    char.hunger = 3
    char.assign_traits(
        {
            "Strength": 3,
            "Dexterity": 2,
            "Intelligence": 2,
            "Brawl": 4,
            "Stealth": 1,
            "Finance": 2,
        }
    )
    return char


@pytest.mark.parametrize(
    "syntax",
    [
        # Hunger arithmetic with a trait other than Hunger. (A trait right
        # after the pool joins it instead; see test_missing_plus_hint.)
        "strength + brawl hunger + surge 2",
        "strength + brawl 1 + finance 2",
        "strength + brawl hunger - finance",
    ],
)
def test_hunger_isnt_hunger(syntax: str, hungry: VChar):
    """Hunger only accepts numbers and Hunger."""
    with pytest.raises(errors.HungerIsntHunger):
        RollParser(hungry, syntax)


@pytest.mark.parametrize(
    "syntax",
    [
        # Hunger and Difficulty swapped
        "dexterity + stealth 5 hunger",
        # A trait in Difficulty
        "strength + brawl 2 3 + surge",
        "strength + brawl 2 finance",
    ],
)
def test_invalid_difficulty(syntax: str, hungry: VChar):
    """Difficulty only accepts numbers."""
    with pytest.raises(errors.InvalidDifficulty):
        RollParser(hungry, syntax)


@pytest.mark.parametrize(
    "syntax,hunger,difficulty",
    [
        ("strength + brawl 2 4 + 1", 2, 5),
        ("strength + brawl 2 4 - 1", 2, 3),
        ("strength + brawl hunger 4 + 4 + 5", 3, 13),
        ("7 3 2 + 1", 3, 3),
    ],
)
def test_difficulty_arithmetic(syntax: str, hunger: int, difficulty: int, hungry: VChar):
    """Difficulty still allows number-only arithmetic."""
    p = RollParser(hungry, syntax)
    assert p.hunger == hunger
    assert p.difficulty == difficulty


@pytest.mark.parametrize(
    "syntax,typed",
    [
        ("strength + brawl hunger + Fin 2", "Fin"),
        ("strength + brawl 1 + lung 2", "lung"),
    ],
)
def test_hunger_isnt_hunger_hint(syntax: str, typed: str, hungry: VChar):
    """The error shows the trait as typed, since the same input may name
    different traits on different characters, and suggests adding it to the
    pool instead."""
    with pytest.raises(errors.HungerIsntHunger) as exc_info:
        RollParser(hungry, syntax)

    message = str(exc_info.value)
    assert f"not `{typed}`" in message
    assert f"*Hint: Did you mean `+ {typed}`?*" in message


@pytest.mark.parametrize("token", ["h", "hu", "hun", "Hung", "hunge", "HUNGER", "current_hunger"])
def test_hunger_prefixes_beat_similar_traits(token: str, hungry: VChar):
    """In the Hunger position, a prefix of "hunger" always means Hunger, even
    when it would also match Hunter or Humanity."""
    hungry.assign_traits({"Hunter": 2})
    p = RollParser(hungry, f"strength + brawl {token} 1")
    assert p.hunger == 3
    assert p.difficulty == 1


@pytest.mark.parametrize(
    "syntax,operand,split",
    [
        # A missing "+" before Surge, the most common misroll in the roll history
        ("strength + brawl surge 2", "brawl surge", "brawl + surge"),
        ("strength + brawl surge hunger", "brawl surge", "brawl + surge"),
        # No operators at all
        ("intelligence finance hunger", "intelligence finance", "intelligence + finance"),
        ("strength + brawl fin 2", "brawl fin", "brawl + fin"),
        # Longer leading traits win
        ("strength + brawl strength dex", "brawl strength dex", "brawl strength + dex"),
        # Several missing +s
        ("strength brawl fin 2", "strength brawl fin", "strength + brawl + fin"),
        # Other inherent traits can go in a pool, so they're suggested
        ("strength + brawl humanity", "brawl humanity", "brawl + humanity"),
        ("str + brawl strength dex fin", "brawl strength dex fin", "brawl strength + dex + fin"),
    ],
)
def test_missing_plus_hint(syntax: str, operand: str, split: str, hungry: VChar):
    """Without a +, words join into one operand. If it isn't a trait but
    splits into traits, the error suggests where the +s go."""
    hungry.assign_traits({"Brawl Strength": 1})
    with pytest.raises(errors.TraitNotFound) as exc_info:
        RollParser(hungry, syntax)

    assert exc_info.value.trait == operand
    assert f"*Hint: Did you mean `{split}`?*" in str(exc_info.value)


@pytest.mark.parametrize(
    "syntax,operand",
    [
        # The first word isn't a trait
        ("strength + lung brawl 2", "lung brawl"),
        # The last word isn't a trait
        ("strength + brawl lung 2", "brawl lung"),
        # A middle word isn't a trait
        ("strength + brawl lung fin 2", "brawl lung fin"),
        # Hunger can't go in a pool, so it's never suggested
        ("strength + hunger brawl 2", "hunger brawl"),
        ("strength + h fin 2", "h fin"),
    ],
)
def test_missing_plus_no_hint(syntax: str, operand: str, hungry: VChar):
    """There's no hint unless every part of the split is a trait, so it never
    suggests an invalid roll."""
    with pytest.raises(errors.TraitNotFound) as exc_info:
        RollParser(hungry, syntax)

    assert exc_info.value.trait == operand
    assert exc_info.value.hint is None
    assert "Hint" not in str(exc_info.value)


def test_missing_plus_search_is_bounded(hungry: VChar):
    """Each run of words is looked up at most once. Every "s" matches some
    trait, so a search trying each way to split them would make about 2^9
    lookups here, rather than at most 10 * 11 / 2."""
    words = ["s"] * (MAX_SPLIT_WORDS - 1) + ["zzz"]
    with patch.object(RollParser, "_is_trait", autospec=True, wraps=RollParser._is_trait) as spy:
        with pytest.raises(errors.TraitNotFound) as exc_info:
            RollParser(hungry, "strength + " + " ".join(words))

    assert exc_info.value.hint is None
    assert spy.call_count <= MAX_SPLIT_WORDS * (MAX_SPLIT_WORDS + 1) // 2


def test_missing_plus_hint_word_limit(hungry: VChar):
    """Operands over the word limit get no hint, and no search."""
    at_limit = " ".join(["brawl"] * MAX_SPLIT_WORDS)
    with pytest.raises(errors.TraitNotFound) as exc_info:
        RollParser(hungry, at_limit)
    assert exc_info.value.hint == f"Did you mean `{at_limit.replace(' ', ' + ')}`?"

    over_limit = " ".join(["s"] * 2000)
    with patch.object(RollParser, "_is_trait", autospec=True) as spy:
        with pytest.raises(errors.TraitNotFound) as exc_info:
            RollParser(hungry, f"strength + {over_limit}")

    assert exc_info.value.hint is None
    spy.assert_not_called()


# Multiword traits


@pytest.fixture
def multiword() -> VChar:
    """A vampire with multiword traits and specialties."""
    char = gen_char("vampire")
    char.hunger = 2
    char.assign_traits({"Wits": 2, "Animal": 1, "Animal Ken": 3, "Brawl": 2, "Ravenous": 1})
    char.add_specialties("Animal Ken", ["Big Cats", "Dogs"])
    char.add_specialties("Brawl", ["Kindred", "Kindred Hunters"])
    return char


@pytest.mark.parametrize(
    "tokens,joined",
    [
        ([], []),
        (["animal", "ken"], ["animal ken"]),
        (["animal", "ken.big", "cats"], ["animal ken.big cats"]),
        (["a", "b", "c", "+", "d", "e"], ["a b c", "+", "d e"]),
        # Numbers and operators never join
        (["wits", "2", "3"], ["wits", "2", "3"]),
        (["3", "wits"], ["3", "wits"]),
        (["wits", "-", "animal"], ["wits", "-", "animal"]),
        # Words that read as Hunger start the Hunger stack
        (["ravenous", "hunger", "3"], ["ravenous", "hunger", "3"]),
        (["ravenous", "h"], ["ravenous", "h"]),
        (["ravenous", "current_hunger"], ["ravenous", "current_hunger"]),
        # But Hunger may be a first word
        (["+", "hunger", "pangs"], ["+", "hunger pangs"]),
    ],
)
def test_join_words(tokens: list[str], joined: list[str]):
    """Adjacent words join into one operand, unless the later reads as Hunger."""
    assert RollParser.join_words(tokens) == joined


@pytest.mark.parametrize(
    "syntax,pool_str,pool",
    [
        ("wits + animal ken", "Wits + Animal Ken", 5),
        ("wits+animal  ken", "Wits + Animal Ken", 5),
        # Only the last word abbreviates
        ("wits + animal k", "Wits + Animal Ken", 5),
        # Exact matches win
        ("wits + animal", "Wits + Animal", 3),
        ("animal ken + animal", "Animal Ken + Animal", 4),
        # Multiword specialties
        ("wits + animal ken.big cats", "Wits + Animal Ken (Big Cats)", 6),
        ("wits + animal ken . big c", "Wits + Animal Ken (Big Cats)", 6),
        ("wits + an.big c", "Wits + Animal Ken (Big Cats)", 6),
        ("wits + brawl.kindred hunters", "Wits + Brawl (Kindred Hunters)", 5),
        ("wits + brawl.kindred", "Wits + Brawl (Kindred)", 5),
        ("animal ken.dogs.big cats", "Animal Ken (Big Cats, Dogs)", 5),
    ],
)
def test_multiword_pools(syntax: str, pool_str: str, pool: int, multiword: VChar):
    """Multiword traits and specialties roll like single words."""
    p = RollParser(multiword, syntax)
    assert p.pool_str == pool_str
    assert p.pool == pool


@pytest.mark.parametrize(
    "syntax,pool_str,hunger,difficulty",
    [
        ("wits + ravenous hunger 3", "Wits + Ravenous", 2, 3),
        ("wits + animal ken h 3", "Wits + Animal Ken", 2, 3),
        ("wits + animal ken 1 3", "Wits + Animal Ken", 1, 3),
        # A Hunger word ends a specialty, too
        ("wits + brawl.kindred h 3", "Wits + Brawl (Kindred)", 2, 3),
    ],
)
def test_multiword_stacks(
    syntax: str, pool_str: str, hunger: int, difficulty: int, multiword: VChar
):
    """Hunger and Difficulty still follow a multiword pool."""
    p = RollParser(multiword, syntax)
    assert p.pool_str == pool_str
    assert p.hunger == hunger
    assert p.difficulty == difficulty


def test_multiword_ambiguous(multiword: VChar):
    """Only the last word abbreviates, so "an k" isn't Animal Ken, and a
    prefix matching several specialties is ambiguous."""
    with pytest.raises(errors.TraitNotFound):
        RollParser(multiword, "wits + an k")
    with pytest.raises(errors.AmbiguousTraitError):
        RollParser(multiword, "wits + brawl.kin")


def test_multiword_expansion(multiword: VChar):
    """Macros store multiword keys as single tokens, which roll from a list."""
    p = RollParser(multiword, "wits + animal k.big", expand_only=True)
    assert p.pool_stack == ["Wits", "+", "Animal Ken.Big Cats"]

    p = RollParser(multiword, [*p.pool_stack, "current_hunger", "3"])
    assert p.pool_str == "Wits + Animal Ken (Big Cats)"
    assert p.pool == 6
    assert p.hunger == 2
    assert p.difficulty == 3


@pytest.mark.parametrize(
    "syntax,pool_str,pool",
    [
        ("wits + beast's fang", "Wits + Beast's Fang", 4),
        ("wits + beast\u2019s fang", "Wits + Beast's Fang", 4),
        ("wits + beast\u2018s f", "Wits + Beast's Fang", 4),
        ("wits + animal ken.dogs'", "Wits + Animal Ken (Dogs')", 6),
        ("wits + animal ken.dogs\u2019", "Wits + Animal Ken (Dogs')", 6),
    ],
)
def test_apostrophes(syntax: str, pool_str: str, pool: int, multiword: VChar):
    """Traits and specialties may have apostrophes, curly or straight."""
    multiword.assign_traits({"Beast's Fang": 2})
    multiword.add_specialties("Animal Ken", ["Dogs'"])

    p = RollParser(multiword, syntax)
    assert p.pool_str == pool_str
    assert p.pool == pool


@pytest.mark.parametrize(
    "syntax,pool_str",
    [
        ("wits + animalken", "Wits + Animal Ken"),
        ("wits + animalk.bigcats", "Wits + Animal Ken (Big Cats)"),
        ("animalken.dogs + wits", "Animal Ken (Dogs) + Wits"),
    ],
)
def test_rolls_ignore_spaces(syntax: str, pool_str: str, multiword: VChar):
    """Names typed without spaces still roll, when nothing matches with them."""
    assert RollParser(multiword, syntax).pool_str == pool_str


def test_mortal_multiword(mortal: VChar):
    """Mortals join words too, so a missing + is a missing trait."""
    mortal.assign_traits({"Animal Ken": 2})
    p = RollParser(mortal, "stren + animal ken 3")
    assert p.pool == 5
    assert p.difficulty == 3

    with pytest.raises(errors.TraitNotFound):
        RollParser(mortal, "stren + brawl animal 3")


@pytest.mark.parametrize(
    "syntax,hunger,difficulty",
    [
        ("stren+br", 2, 3),
        ("stren+br 1", 1, 3),
        ("stren+br 1 4", 1, 4),
        ("stren+br hunger + 1", 3, 3),
    ],
)
def test_default_hunger_and_difficulty(syntax: str, hunger: int, difficulty: int, character: VChar):
    """Defaults fill in a missing Hunger and Difficulty, as macros need."""
    character.hunger = 2
    p = RollParser(character, syntax, default_hunger="current_hunger", default_difficulty="3")
    assert p.hunger == hunger
    assert p.difficulty == difficulty


def test_mortal_default_difficulty(mortal: VChar):
    """A mortal's Hunger position is still read as Difficulty."""
    p = RollParser(mortal, "stren+br 4", default_hunger="current_hunger", default_difficulty="3")
    assert p.difficulty == 4
