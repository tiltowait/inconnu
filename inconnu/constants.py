"""constants.py - Define package-wide constants."""

import os
from types import SimpleNamespace

from dotenv import load_dotenv
from flatdict import FlatDict

load_dotenv()

SUPPORT_URL = "https://discord.com/invite/CPmsdWHUcZ"

INCONNU_ID = int(os.environ["INCONNU_ID"])

# Tracker Stress
DAMAGE = SimpleNamespace(none=".", superficial="/", aggravated="x")

GROUPED_TRAITS = {
    "ATTRIBUTES": {
        "Physical": ["Strength", "Dexterity", "Stamina"],
        "Social": ["Charisma", "Manipulation", "Composure"],
        "Mental": ["Intelligence", "Wits", "Resolve"],
    },
    "SKILLS": {
        "Physical": [
            "Athletics", "Brawl", "Craft",
            "Drive", "Firearms", "Larceny",
            "Melee", "Stealth", "Survival"
        ],
        "Social": [
            "AnimalKen", "Etiquette", "Insight",
            "Intimidation", "Leadership", "Performance",
            "Persuasion", "Streetwise", "Subterfuge"
        ],
        "Mental": [
            "Academics", "Awareness", "Finance",
            "Investigation", "Medicine", "Occult",
            "Politics", "Science", "Technology"
        ],
    }
}

FLAT_TRAITS = sum(FlatDict(GROUPED_TRAITS).values(), [])

UNIVERSAL_TRAITS = ["Willpower", "Hunger", "Humanity", "Surge", "Potency"]

ROUSE_FAIL_COLOR = 0xc70f0f
