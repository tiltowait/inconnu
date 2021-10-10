"""macros/update.py - Macro update commands."""

import re
from distutils.util import strtobool

from . import macro_common
from .. import common
from ..log import Log
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=updating"
__VALID_KEYS = {
    "name": "The macro's name (letters and underscores only)",
    "pool": "The macro's pool",
    "hunger": "Whether to add Hunger to the roll",
    "difficulty": "The macro's default difficulty",
    "rouses": "The number of Rouse checks to make",
    "reroll_rouses": "Whether to re-roll the Rouse checks",
    "comment": "The macro's comment"
}


async def update(ctx, macro: str, syntax: str, character: str):
    """Update a macro."""
    try:
        tip = f"`/macro update` `macro:{macro}` `parameters:PARAMETERS` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        macro = character.find_macro(macro)

        parameters = __parameterize(syntax)
        macro_update = __validate_parameters(character, parameters)
        character.update_macro(macro.name, macro_update)

        await ctx.respond(f"Updated **{character.name}'s** `{macro.name}` macro.")

    except (
        errors.MacroNotFoundError, errors.AmbiguousTraitError, errors.TraitNotFoundError,
        SyntaxError, ValueError
    ) as err:
        if isinstance(err, (SyntaxError, ValueError)):
            Log.log("macro_update_error", user=ctx.author.id, charid=character.id, syntax=syntax)

        keys = [f"`{key}`: {value}" for key, value in __VALID_KEYS.items()]
        instructions = [
            ("Instructions", "Update the macro with one or more KEY=VALUE pairs."),
            ("Valid Keys", "\n".join(keys))
        ]

        await common.present_error(ctx, err, *instructions,
            help_url=__HELP_URL,
            character=character.name
        )
    except common.FetchError:
        pass


def __parameterize(parameters):
    """Convert multi-word parameter/value pairs to a dictionary."""
    parameters = re.sub(r"\s*=\s*", r"=", parameters) # Remove gaps between keys and values
    pattern = re.compile(r"([A-z]+)=")

    params = {}

    match = pattern.match(parameters)
    while match is not None and len(parameters) > 0:
        key = match.groups(0)[0]
        parameters = parameters[match.span()[1]:]

        # Get the value
        match = pattern.search(parameters)
        if match is None:
            value = parameters
            parameters = ""
        else:
            value = parameters[:match.span()[0]]
            parameters = parameters[match.span()[0]:]

        params[key] = value.strip()
        match = pattern.match(parameters)

    if len(parameters) > 0:
        raise SyntaxError(f"Invalid syntax: `{parameters}`.")

    return params


def __validate_parameters(character: VChar, parameters: dict):
    """Parse the update parameters."""
    macro_update = {}

    for key, value in parameters.items():
        # Each parameter should be part of a key=value pair
        if key in macro_update:
            raise SyntaxError(f"Duplicate key: `{key}`.")

        # Valid keys:
        #   name
        #   pool
        #   hunger
        #   difficulty
        #   comment
        #   rouses/rouse
        #   reroll_rouses/reroll
        if key == "name":
            if not macro_common.is_macro_name_valid(value):
                raise ValueError(f"`{value}` is not a valid macro name.")
            macro_update[key] = value

        elif key == "pool":
            pool = macro_common.expand_syntax(character, value)
            macro_update[key] = pool

        elif key == "hunger":
            try:
                value = bool(strtobool(value))
                macro_update[key] = value
            except ValueError:
                raise ValueError("`hunger` requires yes/no or true/false.") from ValueError

        elif key in ["diff", "difficulty"]:
            if not value.isdigit() or int(value) < 0:
                raise ValueError("`difficulty` must be a number greater than 0.")
            macro_update["difficulty"] = int(value)

        elif key == "comment":
            macro_update[key] = value

        elif key in ["rouses", "rouse"]:
            if not value.isdigit() or not 0 <= int(value) <= 3:
                raise ValueError("`rouses` must be a number between 0 and 3.")
            macro_update["rouses"] = int(value)

        elif key in ["reroll_rouses", "reroll", "reroll_rouse"]:
            try:
                value = bool(strtobool(value))
                macro_update[key] = value
            except ValueError:
                raise ValueError("`reroll_rouses` requires yes/no or true/false.") from ValueError

        else:
            raise ValueError(f"Unknown key `{key}`.")

    # Validated the update
    return macro_update