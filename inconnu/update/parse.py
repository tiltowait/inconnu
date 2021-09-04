"""update/parse.py - Defines an interface for updating character traits."""

from . import paramupdate
from ..common import get_character
from ..constants import character_db
from ..display import parse as display

__INSTRUCTIONS = "USAGE: `//update CHAR_NAME PARAMETER=NEW_VALUE ...`"
__INSTRUCTIONS += "\n\tUse `//update help` for a list of parameters."
__INSTRUCTIONS += "\n\tUse `//update help PARAMETER` for a description of that parameter.."

__KEYS = {
    "name": "The character's name",
    "health": "The character's max Health",
    "wp": "The character's max Willpower",
    "humanity": "The character's Humanity",
    "splat": "The type of character: vampire, mortal, or ghoul",
    "sh": "+/- Superficial Health damage",
    "ah": "+/- Aggravated Health damage",
    "sw": "+/- Superficial Willpower damage",
    "aw": "+/- Aggravated Willpower damage",
    "stains": "+/- Stains",
    "cur_xp": "+/- Current XP",
    "total_xp": "+/- Total XP"
}


async def parse(ctx, *args):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    args = list(args) # To allow element removal
    char_name, char_id = get_character(ctx.guild.id, ctx.author.id, args[0])

    if char_id is None:
        err = __character_error_message(ctx.guild.id, ctx.author.id, char_name)
        err += f"\n\n{__INSTRUCTIONS}"

        await ctx.reply(err)
        return

    # Delete args[0] if it was the character name
    if char_name.lower() == args[0].lower():
        del args[0]

    try:
        parameters = __parse_arguments(*args)

        for parameter, new_value in parameters.items():
            __update_character(ctx.guild.id, ctx.author.id, char_id, parameter, new_value)

        await display(ctx, char_name)

    except ValueError as err:
        await ctx.reply(str(err))


def __parse_arguments(*arguments):
    """
    Parse the user's arguments.
    Raises ValueErrors and KeyErrors on exceptions.
    """
    if len(arguments) == 0:
        raise ValueError(__INSTRUCTIONS)

    parameters = {}

    for argument in arguments:
        key, value = argument.split("=")
        key = key.lower()

        if key in parameters:
            raise ValueError(f"You cannot use `{key}` more than once.")

        parameters[key] = value # Don't do any validation here

    return parameters


def __update_character(guildid: int, userid: int, charid: int, param: str, value: str):
    """
    Update one of a character's parameters.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        charid (int): The character's database ID
        param (str): The parameter to update
        value (str): The parameter's new value
    Raises ValueError if the parameter's value is invalid.
    """
    getattr(paramupdate, f"update_{param}")(guildid, userid, charid, value)


def __character_error_message(guildid: int, userid: int, input_name: str) -> str:
    """Create a message informing the user they need to supply a correct character."""
    user_chars = list(character_db.characters(guildid, userid).keys())
    message = None

    if len(user_chars) == 0:
        message = "You have no characters to update."
    else:
        user_chars = list(map(lambda char: f"`{char}`", user_chars))
        message = f"You have no character named `{input_name}`. Options:\n\n"
        message += ", ".join(user_chars)

    return message
