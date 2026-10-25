"""Tests for inconnu/character/impairment.py."""

import pytest

from inconnu.character.impairment import impairment_reminder, incapacitation_reminder
from models import VChar
from tests.characters import gen_char

HEALTHY = "......"
PHYSICAL = "//////"
INCAPACITATED = "xxxxxx"
MENTAL = "/////"
TOTAL_AUTOMATIC = (
    "You are totally impaired. Your physical, social, and mental rolls will receive a -2 penalty."
)


@pytest.fixture(params=["vampire", "ghoul", "mortal", "thin-blood"])
def character(request: pytest.FixtureRequest) -> VChar:
    """A character of each splat."""
    return gen_char(request.param)


def expected_incapacitation(character: VChar) -> str:
    """The incapacitation text for the character's splat."""
    return "You are IN TORPOR!" if character.is_vampire else "You are DEAD!"


@pytest.mark.parametrize("health", [HEALTHY, PHYSICAL, "/xxxxx"])
def test_no_incapacitation(character: VChar, health: str):
    """Characters who aren't incapacitated get no incapacitation reminder."""
    character.health = health
    assert incapacitation_reminder(character) is None


def test_incapacitation(character: VChar):
    """Vampires are in torpor; everyone else is dead."""
    character.health = INCAPACITATED
    assert incapacitation_reminder(character) == expected_incapacitation(character)


@pytest.mark.parametrize(
    "health,willpower,stains,manual,automatic",
    [
        (
            PHYSICAL,
            ".....",
            0,
            "You are physically impaired. Subtract 2 dice from physical pools.",
            "You are physically impaired. Your physical rolls will receive a -2 penalty.",
        ),
        (
            HEALTHY,
            MENTAL,
            0,
            "You are mentally impaired. Subtract 2 dice from social and mental pools.",
            "You are mentally impaired. Your social and mental rolls will receive a -2 penalty.",
        ),
        (
            PHYSICAL,
            MENTAL,
            0,
            "You are totally impaired. Remember to subtract 2 dice from all pools.",
            TOTAL_AUTOMATIC,
        ),
        (
            HEALTHY,
            ".....",
            4,  # Degeneration
            "You are totally impaired. Remember to subtract 2 dice from all pools.",
            TOTAL_AUTOMATIC,
        ),
    ],
)
def test_impairment_reminder(
    character: VChar, health: str, willpower: str, stains: int, manual: str, automatic: str
):
    """Manual reminders tell players to subtract dice; automatic ones say which
    rolls are penalized."""
    character.health = health
    character.willpower = willpower
    character.stains = stains

    assert impairment_reminder(character) == manual
    assert impairment_reminder(character, automatic=True) == automatic


@pytest.mark.parametrize("automatic", [False, True])
def test_impairment_reminder_incapacitated(character: VChar, automatic: bool):
    """Incapacitation takes priority over impairment, in either mode."""
    character.health = INCAPACITATED
    character.willpower = MENTAL

    reminder = impairment_reminder(character, automatic=automatic)
    assert reminder == expected_incapacitation(character)


@pytest.mark.parametrize("automatic", [False, True])
def test_impairment_reminder_unimpaired(character: VChar, automatic: bool):
    """Unimpaired characters get no reminder."""
    assert impairment_reminder(character, automatic=automatic) is None
