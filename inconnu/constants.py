"""constants.py - Define package-wide constants."""

import os
from enum import Enum

from dotenv import load_dotenv
from flatdict import FlatDict

load_dotenv()

SUPPORT_URL = "https://discord.gg/QHnCdSPeEE"
PATREON = "https://www.patreon.com/tiltowait"

INCONNU_ID = int(os.environ["INCONNU_ID"])

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

ATTRIBUTES = set(sum(GROUPED_TRAITS["ATTRIBUTES"].values(), []))
SKILLS = set(sum(GROUPED_TRAITS["SKILLS"].values(), []))
ATTRIBUTES_AND_SKILLS = ATTRIBUTES.union(SKILLS)
FLAT_TRAITS = lambda: sum(FlatDict(GROUPED_TRAITS).values(), [])

UNIVERSAL_TRAITS = ["Willpower", "Hunger", "Humanity", "Surge", "Potency", "Bane"]

ROUSE_FAIL_COLOR = 0xC70F0F


class Damage(str, Enum):
    """An enum for damage types."""

    NONE = "."
    SUPERFICIAL = "/"
    AGGRAVATED = "x"
