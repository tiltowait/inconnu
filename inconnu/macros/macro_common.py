"""macros/macrocommon.py - Common macro utilities."""

import re

from ..databases import MacroDB, CharacterNotFoundError
from ..common import character_db

macro_db = MacroDB()

def is_macro_name_valid(name: str) -> bool:
    """Determines whether a macro name is valid."""
    return re.match(r"^[A-z_]+$", name) is not None

def match_character(guildid: int, userid: int, char_name: str) -> tuple:
    """Find a character by exact name or pick the user's only character."""
    user_chars = character_db.characters(guildid, userid)

    if char_name is None:
        if len(user_chars) == 1:
            return list(user_chars.items())[0]

        if len(user_chars) == 0:
            raise ValueError("You have no characters!")

        # User has too many characters
        names = "\n".join(list(user_chars.keys()))
        err = f"**You must supply a character. Options:**\n\n{names}"
        raise ValueError(err)

    # They've supplied a character
    try:
        return character_db.character(guildid, userid, char_name)
    except CharacterNotFoundError as err:
        raise ValueError(str(err)) from err
