"""character/update/parse.py - Defines an interface for updating character traits."""

import re

import discord
from discord_ui.components import LinkButton

from . import paramupdate
from ..display import display
from ... import common
from ...log import Log
from ...vchar import VChar

__MATCHES = {}

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
    "unspent_xp": "+/- Unspent XP",
    "lifetime_xp": "+/- Total Lifetime XP",
    "hunger": "+/- The character's Hunger",
    "potency": "+/- The character's Blood Potency"
}

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=tracker-updates"


async def update(ctx, parameters: str, character=None, update_message=None, player=None):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    args = re.sub(r":", r"=", parameters) # Some people think colons work ...
    args = re.sub(r"([+-])=", r"=\g<1>", args) # Let +/-= work, for the CS nerds
    args = re.sub(r"\s*=+\s*", r"=", args) # Remove gaps between keys and values
    args = list(args.split()) # To allow element removal

    if len(args) == 0:
        await update_help(ctx)
        return

    try:
        owner = await common.player_lookup(ctx, player)
        tip = f"`/character update` `parameters:{parameters}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        parameters = __parse_arguments(*args)
        updates = []

        for parameter, new_value in parameters.items():
            update_msg = __update_character(character, parameter, new_value)
            updates.append(update_msg)

        if update_message is None:
             # We only want to set the update message if we didn't get a customized display message
            update_message = "\n".join(updates)

        Log.log("update", user=ctx.author.id, guild=ctx.guild.id, charid=character.id, syntax=" ".join(args))
        await display(ctx, character, owner=player, message=update_message)

    except (SyntaxError, ValueError) as err:
        Log.log("update_error", user=ctx.author.id, guild=ctx.guild.id, charid=character.id, syntax=" ".join(args))
        await update_help(ctx, err)
    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
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

        if key in parameters:
            raise ValueError(f"You cannot use `{key}` more than once.")

        if key not in __MATCHES:
            raise ValueError(f"Unknown parameter: `{key}`.")

        key = __MATCHES[key] # Get the canonical key

        value = split[1]
        if len(value) == 0:
            raise ValueError(f"No value given for `{key}`.")

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

    inst = "To update a character, use `/character update` with one or more `KEY=VALUE` pairs."
    embed.add_field(name="Instructions", value=inst, inline=False)

    parameters = [f"**{key}:** {val}" for key, val in __KEYS.items()]
    parameters = "\n".join(parameters)
    embed.add_field(name="Options", value=parameters, inline=False)

    embed.set_footer(text="You may modify more than one tracker at a time.")

    button = LinkButton(
        "http://www.inconnu-bot.com/#/character-tracking?id=tracker-updates",
        label="Full Documentation"
    )
    await ctx.respond(embed=embed, components=[button], hidden=hidden)

# We do flexible matching for the keys. Many of these are the same as RoD's
# keys, while others have been observed in syntax error logs. This should be
# a little more user-friendly.

def __setup_matches():
    """Register all the update keys."""
    __register_keys("name")
    __register_keys("health", "hp")
    __register_keys("willpower", "wp", "w")
    __register_keys("humanity", "hm")
    __register_keys("splat", "type")
    __register_keys(
        "sh", "sd", "shp", "suphp", "suph", "supd", "superficialhealth",
        "superficialdamage"
    )
    __register_keys("ah", "ad", "ahp", "agghp", "aggd", "aggh", "agghealth", "aggdamage")
    __register_keys("sw", "swp", "supwp", "supw", "superficialwillpower")
    __register_keys("aw", "awp", "aggwp", "aggw", "aggwillpower")
    __register_keys("stains", "stain", "s")
    __register_keys(
        "current_xp", "xp_current", "current_exp", "exp_current", "currentxp",
        "currentexp", "xpcurrent", "expcurrent", "cxp",
        "unspent_xp", "xp_unspent", "unspent_exp", "exp_unspent", "unspentxp",
        "unspentexp", "xpunspent", "expunspent", "uxp"
    )
    __register_keys(
        "total_xp", "xp_total", "total_exp", "exp_total", "totalxp",
        "totalexp", "xptotal", "exptotal", "txp",
        "lifetimexp", "xplifetime", "explifetime", "lxp", "lifetime_xp", "life_time_xp"
    )
    __register_keys("hunger", "h")
    __register_keys("potency", "bp", "p")


def __register_keys(canonical, *alternates):
    """Register an update key along with some alternates."""
    __MATCHES[canonical] = canonical
    for alternate in alternates:
        if alternate in __MATCHES:
            raise KeyError(f"{alternate} is already an update parameter.")
        __MATCHES[alternate] = canonical


__setup_matches()
