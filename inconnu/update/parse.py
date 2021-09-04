"""update/parse.py - Defines an interface for updating character traits."""

from . import paramupdate
from ..constants import character_db
from ..databases import CharacterNotFoundError
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
    """Process the user's arguments."""
    if len(args) < 2:
        await ctx.reply(__INSTRUCTIONS)
        return

    args = list(args) # To allow element deletion
    char_name = args[0]
    del args[0]

    try:
        char_id = character_db.character_id(ctx.guild.id, ctx.author.id, char_name)
        parameters = __parse_arguments(*args)

        for parameter, new_value in parameters.items():
            __update_character(ctx.guild.id, ctx.author.id, char_id, parameter, new_value)

        await display(ctx, char_name)


    except (ValueError, CharacterNotFoundError) as err:
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
