"""constants.py - Define package-wide constants."""

from collections import namedtuple

from .databases import CharacterDB

character_db = CharacterDB()
valid_splats = {"vampire": 0, "ghoul": 1, "mortal": 2}

# Tracker Stress
__Damage = namedtuple("Damage", ["none", "superficial", "aggravated"]) #pylint: disable=invalid-name
DAMAGE = __Damage(".", "/", "x")
