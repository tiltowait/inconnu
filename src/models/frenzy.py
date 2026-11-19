"""models/frenzy.py - Frenzy check modifiers."""

from enum import StrEnum
from typing import Literal, Self

# The most flat bonus dice a frenzy check may take
MAX_FRENZY_BONUS = 7


class FrenzyAdvantage(StrEnum):
    """An advantage that aids in resisting frenzy, with its name and bonus
    dice. The Dream grants none; it re-rolls failures instead."""

    display: str
    dice: int

    def __new__(cls, value: str, display: str, dice: int) -> Self:
        """Create a member from its value, name, and bonus dice."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.display = display
        member.dice = dice
        return member

    COLD_DEAD_HUNGER = ("cold_dead_hunger", "Cold Dead Hunger", 2)
    GENTLE_MIND = ("gentle_mind", "Gentle Mind", 4)
    JEWEL_IN_THE_GARDEN = ("jewel_in_the_garden", "Jewel in the Garden", 4)
    THE_DREAM = ("the_dream", "The Dream", 0)
    THE_HEART_OF_DARKNESS = ("the_heart_of_darkness", "The Heart of Darkness", 2)


type FrenzyPenalty = Literal["brujah", "malkavian"]
