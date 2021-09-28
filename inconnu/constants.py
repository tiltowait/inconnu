"""constants.py - Define package-wide constants."""

import os
from types import SimpleNamespace

INCONNU_ID = int(os.environ["INCONNU_ID"])

# Tracker Stress
DAMAGE = SimpleNamespace(none=".", superficial="/", aggravated="x")

SKILLS_AND_ATTRIBUTES = [
    "strength", "dexterity", "stamina", "charisma", "manipulation", "composure",
    "intelligence", "wits", "resolve", "athletics", "brawl", "craft", "drive", "firearms",
    "larceny", "melee", "stealth", "survival", "animalken", "etiquette", "insight",
    "intimidation", "leadership", "performance", "persuasion", "streetwise", "subterfuge",
    "academics", "awareness", "finance", "investigation", "medicine", "occult", "politics",
    "science", "technology"
]

UNIVERSAL_TRAITS = ["willpower", "hunger", "humanity", "surge"]
