"""models/impairment.py - Impairment rules: which rolls an impairment penalizes."""

from enum import Flag, StrEnum, auto
from typing import Self

from constants import MENTAL_SOCIAL_ATTRIBUTES, PHYSICAL_ATTRIBUTES

# The number of dice impairment removes from a pool
IMPAIRMENT_DICE = 2


class RollCategory(Flag):
    """The Attribute categories in a roll's pool. Mental covers social and mental
    Attributes."""

    NONE = 0
    PHYSICAL = auto()
    MENTAL = auto()
    MIXED = PHYSICAL | MENTAL

    @classmethod
    def from_pool(cls, pool: str | None) -> Self:
        """The categories of the Attributes in a pool string. Skills are ignored,
        since they can pair with any Attribute. Pools without Attributes, such as
        number-only pools, have no category."""
        category = cls(cls.NONE)  # Constructed via cls so the type stays Self
        if pool:
            elements = set(pool.split())
            if elements & PHYSICAL_ATTRIBUTES:
                category |= cls.PHYSICAL
            if elements & MENTAL_SOCIAL_ATTRIBUTES:
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


class ImpairmentCategory(StrEnum):
    """A per-roll choice of Impairment category, overriding the one detected from
    the pool's Attributes. Ignore means the roll isn't penalized at all."""

    IGNORE = "ignore"
    PHYSICAL = "physical"
    MENTAL = "mental"

    @classmethod
    def from_option(cls, value: str | None) -> Self | None:
        """The choice from a command option's value, or None if none was chosen."""
        return cls(value) if value else None

    @property
    def label(self) -> str:
        """The choice's display name."""
        match self:
            case ImpairmentCategory.IGNORE:
                return "Ignore"
            case ImpairmentCategory.PHYSICAL:
                return "Physical"
            case ImpairmentCategory.MENTAL:
                return "Mental/Social"

    @property
    def roll_category(self) -> RollCategory:
        """The roll category the choice stands for. Ignore stands for no category,
        which no Impairment penalizes."""
        match self:
            case ImpairmentCategory.PHYSICAL:
                return RollCategory.PHYSICAL
            case ImpairmentCategory.MENTAL:
                return RollCategory.MENTAL
            case ImpairmentCategory.IGNORE:
                return RollCategory.NONE
