"""macros/roll.py - Rolling character macros."""

import re

from ..vr import perform_roll, display_outcome
from . import macro_common
from .. import common
from ..misc import rouse
from ..vchar import errors

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=rolling"


async def roll(ctx, syntax: str, character=None):
    """Roll a macro."""
    try:
        tip = f"`/vm` `syntax:{syntax}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        macro_stack, hunger, difficulty = __normalize_syntax(syntax) # pylint: disable=unbalanced-tuple-unpacking

        if not macro_common.is_macro_name_valid(macro_stack[0]):
            raise ValueError("Macro names may only contain letters and underscores.")

        macro = character.find_macro(macro_stack.pop(0))
        parameters = macro.pool
        parameters.extend(macro_stack)

        # Macros can contain hunger by default, but the user can override
        if hunger is None:
            hunger = "hunger" if macro.hunger else "0"

        parameters.append(hunger)
        parameters.append(difficulty or macro.difficulty)

        results = perform_roll(character, parameters)

        # We show the rouse check first, because display_outcome() is blocking
        await __rouse(ctx, character, macro)
        await display_outcome(ctx, ctx.user, character, results, macro.comment)


    except (ValueError, errors.MacroNotFoundError) as err:
        await common.present_error(ctx, err, character=character.name, help_url=__HELP_URL)
    except SyntaxError:
        err = f"**Unknown syntax:** `{syntax}`"
        err += "\n**Usage:** `/vm <macro_name> [hunger] [difficulty]`"
        err += "\n\nYou may add simple math after `macro_name`."
        err += "\n `hunger` and `difficulty` are optional."
        await common.present_error(ctx, err, help_url=__HELP_URL)
        return
    except common.FetchError:
        pass


async def __rouse(ctx, character, macro):
    """Perform a rouse check."""
    if macro.comment is not None:
        purpose = macro.comment
    else:
        purpose = f"{macro.name} macro"
    msg = "Hunger gained does not apply to the roll."

    if macro.rouses > 0:
        await rouse(
            ctx, macro.rouses, character.name, purpose, macro.reroll_rouses,
            oblivion=macro.staining, message=msg
        )


def __normalize_syntax(syntax: str):
    syntax = re.sub(r"([+-])", r" \g<1> ", syntax)
    stack = syntax.split()
    params = []

    while len(stack) > 1 and stack[-2] not in ["+", "-"]:
        params.insert(0, stack.pop())

    params.insert(0, stack)

    if len(params) == 1:
        params.append(None)

    if len(params) == 2:
        params.append(None)

    # At this point, the stack contains the following items
    # 0: Pool (list that will be parsed by the standard roll parser)
    # 1: Hunger ("0" or the user's input)
    # 2: Difficulty (None or the user's input)

    # We validate the pool stack later, but we will validate hunger and difficulty
    # here. We don't modify anything; the roll parser will do that for us. Insteat,
    # we simply check for validity.

    if params[1] is not None and params[1].lower() != "hunger": # "hunger" is a valid option here
        if not 0 <= int(params[1]) <= 5:
            raise ValueError("Hunger must be between 0 and 5.")

    difficulty = params[2]
    if difficulty is not None:
        difficulty = int(difficulty)
        if difficulty < 0:
            raise ValueError("Difficulty cannot be less than 0.")

    return params
