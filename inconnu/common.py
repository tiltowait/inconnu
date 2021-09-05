"""common.py - Commonly used functions."""

from .databases import CharacterNotFoundError
from .constants import character_db

def get_character(guildid: int, userid: int, *args) -> tuple:
    """
    Intelligently retrieve the user's character.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        potential_name (str): The potential name of the character
    Returns (tuple): The character name and ID.

    If the user didn't supply a name but has only one character, we return it.
    This function should never raise an exception in normal usage.
    """
    potential_name = args[0] if len(args) > 0 else ''
    char_name = None
    char_id = None

    try:
        char_name, char_id = character_db.character(guildid, userid, potential_name)
    except CharacterNotFoundError:
        pass

    if char_id is None:
        user_chars = character_db.characters(guildid, userid)
        if len(user_chars) == 1:
            # The potential name is only potential, so let's give their only character
            char_name, char_id = list(user_chars.items())[0]

    return (char_name, char_id) # May be null or filled


def character_options_message(guildid: int, userid: int, input_name: str) -> str:
    """Create a message informing the user they need to supply a correct character."""
    user_chars = list(character_db.characters(guildid, userid).keys())
    message = None

    if len(user_chars) == 0:
        message = "You have no characters!"
    else:
        user_chars = list(map(lambda char: f"`{char}`", user_chars))
        message = f"You have no character named `{input_name}`. Options:\n\n"
        message += ", ".join(user_chars)

    return message


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes"}

    pluralized = f"{value} {noun}"
    if value > 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized
