"""character/update/parse.py - Defines an interface for updating character traits."""

import re

import discord
from discord_ui.components import LinkButton

from . import paramupdate
from ..display import display
from ... import common
from ... import stats
from ...vchar import VChar

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

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=tracker-updates"


async def update(ctx, parameters: str, character=None, update_message=None):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    args = re.sub(r"\s+=\s+", r"=", parameters) # Remove gaps between keys and values
    args = list(args.split()) # To allow element removal

    if len(args) == 0:
        await update_help(ctx)
        return

    try:
        tip = f"`/character update` `parameters:{parameters}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        parameters = __parse_arguments(*args)
        updates = []

        for parameter, new_value in parameters.items():
            update_msg = __update_character(character, parameter, new_value)
            updates.append(update_msg)

        if update_message is None:
             # We only want to set the update message if we didn't get a customized display message
            update_message = "\n".join(updates)

        await display(ctx, character, message=update_message)

    except (SyntaxError, ValueError) as err:
        stats.Stats.log_update_error(character.id, " ".join(args))
        await update_help(ctx, err)
    except common.FetchError:
        pass


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


def __update_character(character: VChar, param: str, value: str) -> str:
    """
    Update one of a character's parameters.
    Args:
        character (VChar): The character being updated
        param (str): The parameter to update
        value (str): The parameter's new value
    Raises ValueError if the parameter's value is invalid.
    """
    return getattr(paramupdate, f"update_{param}")(character, value)


async def update_help(ctx, err=None, hidden=True):
    """Display a help message that details the available keys."""
    embed = discord.Embed(
        title="Character Tracking",
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

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
    await ctx.respond(embed=embed, components=[button], hidden=hidden)
