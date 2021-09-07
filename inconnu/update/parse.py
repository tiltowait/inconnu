"""update/parse.py - Defines an interface for updating character traits."""

import re

import discord
from discord_ui.components import LinkButton

from . import paramupdate
from ..common import get_character
from ..constants import character_db
from ..display import parse as display

__KEYS = {
    "name": "The character's name",
    "health": "The character's max Health",
    "wp": "The character's max Willpower",
    "humanity": "The character's Humanity",
    "splat": "The type of character: `vampire`, `mortal`, or `ghoul`",
    "sh": "+/- Superficial Health damage",
    "ah": "+/- Aggravated Health damage",
    "sw": "+/- Superficial Willpower damage",
    "aw": "+/- Aggravated Willpower damage",
    "stains": "+/- Stains",
    "current_xp": "+/- Current XP",
    "total_xp": "+/- Total XP",
    "hunger": "+/- The character's Hunger"
}


async def parse(ctx, args: str):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    args = re.sub(r"\s+=\s+", r"=", args) # Remove gaps between keys and values
    args = list(args.split()) # To allow element removal

    if len(args) == 0:
        await __display_help(ctx)
        return

    char_name, char_id = get_character(ctx.guild.id, ctx.author.id, *args)

    if char_id is None:
        err = __character_error_message(ctx.guild.id, ctx.author.id, char_name)
        await __display_help(ctx, err)
        return

    # Delete args[0] if it was the character name
    if char_name.lower() == args[0].lower():
        del args[0]

    try:
        parameters = __parse_arguments(*args)

        for parameter, new_value in parameters.items():
            __update_character(ctx.guild.id, ctx.author.id, char_id, parameter, new_value)

        await display(ctx, char_name)

    except (SyntaxError, ValueError) as err:
        await __display_help(ctx, err)


def __parse_arguments(*arguments):
    """
    Parse the user's arguments.
    Raises ValueErrors and KeyErrors on exceptions.
    """
    if len(arguments) == 0:
        raise ValueError("You must supply some parameters!")

    parameters = {}

    for argument in arguments:
        split = argument.split("=")
        key = split[0].lower()

        if len(split) != 2:
            err = "Parameters must be in `key = value` pairs."
            if key not in __KEYS:
                err += f" Also, `{key}` is not a valid option."
            raise SyntaxError(err)

        value = split[1]

        if key in parameters:
            raise ValueError(f"You cannot use `{key}` more than once.")

        if key not in __KEYS:
            raise ValueError(f"Unknown parameter: `{key}`.")

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


async def __display_help(ctx, err=None):
    """Display a help message that details the available keys."""
    embed = discord.Embed(
        title="Character Tracking",
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

    if err is not None:
        embed.add_field(name="Error", value=str(err), inline=False)

    instructions = "To update a character, use `//update CHARACTER key=value ...`"
    embed.add_field(name="Instructions", value=instructions, inline=False)

    parameters = [f"**{key}:** {val}" for key, val in __KEYS.items()]
    parameters = "\n".join(parameters)
    embed.add_field(name="Options", value=parameters, inline=False)

    embed.set_footer(text="You may modify more than one tracker at a time.")

    button = LinkButton(
        "http://www.inconnu-bot.com/#/character-tracking?id=tracker-updates",
        label="Full Documentation"
    )
    await ctx.reply(embed=embed, components=[button])
