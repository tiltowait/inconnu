"""constants.py - Define package-wide constants."""

from enum import Flag, StrEnum, auto
from itertools import chain
from typing import Self, cast

from flatdict import FlatDict

SUPPORT_URL = "https://discord.gg/QHnCdSPeEE"
PATREON = "https://www.patreon.com/tiltowait"

GROUPED_TRAITS = {
    "ATTRIBUTES": {
        "Physical": ["Strength", "Dexterity", "Stamina"],
        "Social": ["Charisma", "Manipulation", "Composure"],
        "Mental": ["Intelligence", "Wits", "Resolve"],
    },
    "SKILLS": {
        "Physical": [
            "Athletics",
            "Brawl",
            "Craft",
            "Drive",
            "Firearms",
            "Larceny",
            "Melee",
            "Stealth",
            "Survival",
        ],
        "Social": [
            "AnimalKen",
            "Etiquette",
            "Insight",
            "Intimidation",
            "Leadership",
            "Performance",
            "Persuasion",
            "Streetwise",
            "Subterfuge",
        ],
        "Mental": [
            "Academics",
            "Awareness",
            "Finance",
            "Investigation",
            "Medicine",
            "Occult",
            "Politics",
            "Science",
            "Technology",
        ],
    },
}


ATTRIBUTES = set(chain.from_iterable(GROUPED_TRAITS["ATTRIBUTES"].values()))
SKILLS = set(chain.from_iterable(GROUPED_TRAITS["SKILLS"].values()))
ATTRIBUTES_AND_SKILLS = ATTRIBUTES.union(SKILLS)

# Impairment penalizes pools by their traits' category
PHYSICAL_TRAITS = set(chain.from_iterable(group["Physical"] for group in GROUPED_TRAITS.values()))
MENTAL_SOCIAL_TRAITS = set(
    chain.from_iterable(
        group[category] for group in GROUPED_TRAITS.values() for category in ("Social", "Mental")
    )
)

DISCIPLINES = [
    "Animalism",
    "Auspex",
    "BloodSorcery",
    "Celerity",
    "Dominate",
    "Fortitude",
    "Obeah",
    "Obfuscate",
    "Oblivion",
    "Potence",
    "Presence",
    "Protean",
    "Valeren",
    "Vicissitude",
    "WarriorValeren",
    "WatcherValeren",
]

UNIVERSAL_TRAITS = ["Willpower", "Hunger", "Humanity", "Surge", "Potency", "Bane"]
RESERVED_TRAITS = UNIVERSAL_TRAITS + ["current_hunger"]

ROUSE_FAIL_COLOR = 0xC70F0F


class Damage(StrEnum):
    """An enum for damage types."""

    NONE = "."
    SUPERFICIAL = "/"
    AGGRAVATED = "x"


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

    def penalizes(self, category: RollCategory) -> bool:
        """Whether this impairment penalizes a roll of the given category. Rolls
        without a category, such as number-only pools, are never penalized."""
        physical = Impairment.PHYSICAL in self and RollCategory.PHYSICAL in category
        mental = Impairment.MENTAL in self and RollCategory.MENTAL in category
        return physical or mental


def get_standard_traits() -> list[str]:
    """Generate a flattened list of all standard traits. We use a generator
    function to remove any possibility of modifying the source list."""
    trait_lists = cast(list[list[str]], FlatDict(GROUPED_TRAITS).values())
    return list(chain.from_iterable(trait_lists))
