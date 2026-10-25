"""models/impairment.py - Impairment rules: which rolls an impairment penalizes."""

from enum import Flag, auto
from typing import Self

from constants import MENTAL_SOCIAL_TRAITS, PHYSICAL_TRAITS

# The number of dice impairment removes from a pool
IMPAIRMENT_DICE = 2


class RollCategory(Flag):
    """The trait categories in a roll's pool. Mental covers social and mental traits."""

    NONE = 0
    PHYSICAL = auto()
    MENTAL = auto()
    MIXED = PHYSICAL | MENTAL

    @classmethod
    def from_pool(cls, pool: str | None) -> Self:
        """The categories of the Attributes and Skills in a pool string. Pools
        without any, such as number-only pools, have no category."""
        category = cls(cls.NONE)  # Constructed via cls so the type stays Self
        if pool:
            elements = set(pool.split())
            if elements & PHYSICAL_TRAITS:
                category |= cls.PHYSICAL
            if elements & MENTAL_SOCIAL_TRAITS:
                category |= cls.MENTAL
        return category


class Impairment(Flag):
    """A character's impairment. Mental impairment covers social and mental pools."""

    NONE = 0
    PHYSICAL = auto()
    MENTAL = auto()
    TOTAL = PHYSICAL | MENTAL

    @property
    def description(self) -> str:
        """The impairment's display name."""
        match self:
            case Impairment.PHYSICAL:
                return "physical"
            case Impairment.MENTAL:
                return "mental"
            case Impairment.TOTAL:
                return "total"
            case _:
                return "none"

    def penalizes(self, category: RollCategory) -> bool:
        """Whether this impairment penalizes a roll of the given category. Rolls
        without a category, such as number-only pools, are never penalized."""
        physical = Impairment.PHYSICAL in self and RollCategory.PHYSICAL in category
        mental = Impairment.MENTAL in self and RollCategory.MENTAL in category
        return physical or mental
