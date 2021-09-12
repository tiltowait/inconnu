"""constants.py - Define package-wide constants."""

from types import SimpleNamespace

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
