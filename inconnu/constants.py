"""constants.py - Define package-wide constants."""

import re

from collections import namedtuple

# Tracker Stress
__Damage = namedtuple("Damage", ["none", "superficial", "aggravated"]) #pylint: disable=invalid-name
DAMAGE = __Damage(".", "/", "x")

SKILLS_AND_ATTRIBUTES = [
    "strength", "dexterity", "stamina", "charisma", "manipulation", "composure",
    "intelligence", "wits", "resolve", "athletics", "brawl", "craft", "drive", "firearms",
    "larceny", "melee", "stealth", "survival", "animalken", "etiquette", "insight",
    "intimidation", "leadership", "performance", "persuasion", "streetwise", "subterfuge",
    "academics", "awareness", "finance", "investigation", "medicine", "occult", "politics",
    "science", "technology"
]

VALID_DB_KEY_PATTERN = re.compile(r"^[A-z_]+$")
