"""update/parse.py - Defines an interface for updating character traits."""

import re

import discord
from discord_ui.components import LinkButton

from . import paramupdate
from .. import common
from ..display import parse as display

__KEYS = {
    "name": "The character's name",
    "health": "The character's max Health",
    "willpower": "The character's max Willpower",
    "humanity": "The character's Humanity",
    "splat": "The type of character: `vampire`, `mortal`, or `ghoul`",
    "sh": "+/- Superficial Health damage",
    "ah": "+/- Aggravated Health damage",
    "sw": "+/- Superficial Willpower damage",
    "aw": "+/- Aggravated Willpower damage",
    "stains": "+/- Stains",
    "current_xp": "+/- Current XP",
    "total_xp": "+/- Total XP",
    "hunger": "+/- The character's Hunger",
    "potency": "+/- The character's Blood Potency"
}


async def parse(ctx, parameters: str, character=None):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    args = re.sub(r"\s+=\s+", r"=", parameters) # Remove gaps between keys and values
    args = list(args.split()) # To allow element removal

    if len(args) == 0:
        await __display_help(ctx)
        return

    try:
        char_name, char_id = await common.match_character(ctx.guild.id, ctx.author.id, character)
        parameters = __parse_arguments(*args)

        async with common.character_db.conn.transaction():
            for parameter, new_value in parameters.items():
                if parameter == "name":
                    char_name = new_value

                await __update_character(char_id, parameter, new_value)

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


async def __update_character(charid: int, param: str, value: str):
    """
    Update one of a character's parameters.
    Args:
        charid (int): The character's database ID
        param (str): The parameter to update
        value (str): The parameter's new value
    Raises ValueError if the parameter's value is invalid.
    """
    await getattr(paramupdate, f"update_{param}")(charid, value)


async def __display_help(ctx, err=None):
    """Display a help message that details the available keys."""
    embed = discord.Embed(
        title="Character Tracking",
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

    if err is not None:
        embed.add_field(name="Error", value=str(err), inline=False)

    instructions = "To update a character, use one or more `KEY=VALUE` pairs."
    embed.add_field(name="Instructions", value=instructions, inline=False)

    parameters = [f"**{key}:** {val}" for key, val in __KEYS.items()]
    parameters = "\n".join(parameters)
    embed.add_field(name="Options", value=parameters, inline=False)

    embed.set_footer(text="You may modify more than one tracker at a time.")

    button = LinkButton(
        "http://www.inconnu-bot.com/#/character-tracking?id=tracker-updates",
        label="Full Documentation"
    )
    await ctx.respond(embed=embed, components=[button], hidden=True)
