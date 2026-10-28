"""Test the roll syntax parser."""

import pytest

import errors
from inconnu.vr.parse import needs_character
from inconnu.vr.rollparser import RollParser, eval_expr
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


@pytest.mark.parametrize("syntax", ["stren+br 2 3", "stren+br stren 3", "stren+br finance 3"])
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


@pytest.mark.parametrize("expr,value", [("7", 7), ("3 + 4", 7), ("3 - 4", -1), ("- 2 + + 3", 1)])
def test_eval_expr(expr: str, value: int):
    """Addition, subtraction, and unary signs are evaluated."""
    assert eval_expr(expr) == value


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
        # A missing "+" before Surge, the most common misroll in the roll history
        "strength + brawl surge 2",
        "strength + brawl surge hunger",
        # No operators at all
        "intelligence finance hunger",
        # Traits as Hunger
        "strength + brawl finance 2",
        "strength + brawl strength resolve",
        # Hunger arithmetic with a trait other than Hunger
        "strength + brawl hunger + surge 2",
        "strength + brawl 1 + finance 2",
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
        ("strength + brawl surge 2", "surge"),
        ("intelligence finance hunger", "finance"),
        ("strength + brawl fin 2", "fin"),
        ("strength + brawl hunger + Fin 2", "Fin"),
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


def test_hunger_isnt_a_trait(hungry: VChar):
    """A word that isn't a trait is still the wrong kind of Hunger."""
    with pytest.raises(errors.HungerIsntHunger, match="not `lung`"):
        RollParser(hungry, "strength + brawl lung 2")


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
