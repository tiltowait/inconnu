"""common.py - Commonly used functions."""

import discord

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
    if value != 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized


async def display_error(ctx, char_name, error):
    """Display an error in a nice embed."""
    embed = discord.Embed(
        title="Error",
        description=str(error),
        color=0xFF0000
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    if hasattr(ctx, "reply"):
        await ctx.reply(embed=embed)
    else:
        await ctx.respond(embed=embed, hidden=True)
