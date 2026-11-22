"""constants.py - Define package-wide constants."""

from enum import StrEnum
from itertools import chain
from typing import cast

from flatdict import FlatDict

SUPPORT_URL = "https://discord.gg/QHnCdSPeEE"
PATREON = "https://www.patreon.com/tiltowait"
PATREON_PRICE = "$3/mo"

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
            "Animal Ken",
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

# Impairment penalizes pools by their Attributes' category. Skills don't count,
# because rolls freely pair Attributes and Skills across categories (e.g.
# Composure + Firearms or Intelligence + Brawl).
PHYSICAL_ATTRIBUTES = set(GROUPED_TRAITS["ATTRIBUTES"]["Physical"])
MENTAL_SOCIAL_ATTRIBUTES = set(
    GROUPED_TRAITS["ATTRIBUTES"]["Social"] + GROUPED_TRAITS["ATTRIBUTES"]["Mental"]
)

DISCIPLINES = [
    "Animalism",
    "Auspex",
    "Blood Sorcery",
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
    "Warrior Valeren",
    "Watcher Valeren",
]

UNIVERSAL_TRAITS = ["Willpower", "Hunger", "Humanity", "Surge", "Potency", "Bane"]
RESERVED_TRAITS = UNIVERSAL_TRAITS + ["current_hunger"]

ROUSE_FAIL_COLOR = 0xC70F0F

MAX_PROFILE_LENGTH = 1024  # Biography and description, each
MAX_CONVICTIONS = 3
MAX_CONVICTION_LENGTH = 200

# Sheet limits. All minimums are 0. Servers' max Hunger setting only caps
# rolls, never the sheet
MAX_TRAIT_RATING = 5
MAX_HUMANITY = 10
MAX_STAINS = 10
MAX_POTENCY = 10
MAX_THIN_BLOOD_POTENCY = 2
MAX_HUNGER = 5


class Damage(StrEnum):
    """An enum for damage types."""

    NONE = "."
    SUPERFICIAL = "/"
    AGGRAVATED = "x"


class Theme(StrEnum):
    """Emoji themes. The value is the themed emoji names' prefix."""

    STANDARD = ""
    CITRUS_SHERBERT = "peach"  # Discord's spelling
    BRUISED = "bruised"

    @property
    def human_name(self) -> str:
        """Human-readable name."""
        match self:
            case Theme.STANDARD:
                return "Standard"
            case Theme.CITRUS_SHERBERT:
                return "Citrus Sherbert"
            case Theme.BRUISED:
                return "Bruised"

    @property
    def description(self) -> str:
        """A user-facing description."""
        match self:
            case Theme.STANDARD:
                return ""
            case Theme.CITRUS_SHERBERT:
                return "Complements the Discord theme."
            case Theme.BRUISED:
                return "Blood and bone tones, like the web app."


def get_standard_traits() -> list[str]:
    """Generate a flattened list of all standard traits. We use a generator
    function to remove any possibility of modifying the source list."""
    trait_lists = cast(list[list[str]], FlatDict(GROUPED_TRAITS).values())
    return list(chain.from_iterable(trait_lists))


def name_key(name: str) -> str:
    """A trait name without case or spaces, as lookups compare them:
    "Animal Ken", "animalken", and "AnimalKen" are all "animalken"."""
    return name.casefold().replace(" ", "")


def core_trait(name: str) -> str | None:
    """The standard Attribute or Skill a name refers to, ignoring case and
    spaces ("animalken" is Animal Ken), or None."""
    return _CORE_TRAITS.get(name_key(name))


_CORE_TRAITS = {name_key(name): name for name in get_standard_traits()}
