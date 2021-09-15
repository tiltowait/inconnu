"""macros/roll.py - Rolling character macros."""

import re

from ..roll import perform_roll, display_outcome
from . import macro_common
from .. import common
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=rolling"


async def process(ctx, syntax: str, character=None):
    """Roll a macro."""
    macro_name = None
    hunger = 0
    difficulty = 0

    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
    except errors.UnspecifiedCharacterError as err:
        tip = f"`/vm` `syntax:{syntax}` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return

    try:
        macro_stack, hunger, difficulty = __normalize_syntax(syntax) # pylint: disable=unbalanced-tuple-unpacking

        if not macro_common.is_macro_name_valid(macro_stack[0]):
            raise ValueError("Macro names may only contain letters and underscores.")

        macro = character.find_macro(macro_stack.pop(0))
        parameters = macro.pool
        parameters.extend(macro_stack)
        parameters.append(hunger)
        parameters.append(difficulty or macro.difficulty)

        results = perform_roll(character, *parameters)
        await display_outcome(ctx, character, results, macro.comment)

    except errors.MacroNotFoundError as err:
        await common.display_error(ctx, character.name, err, __HELP_URL)
    except ValueError as err:
        # The user may have deleted a trait, which means the macro is invalid.
        await common.display_error(ctx, character.name, str(err), __HELP_URL)
    except SyntaxError:
        err = f"**Unknown syntax:** `{syntax}`"
        err += "\n**Usage:** `/vm <macro_name> [hunger] [difficulty]`"
        err += "\n\nYou may add simple math after `macro_name`."
        err += "\n `hunger` and `difficulty` are optional."
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return


def __normalize_syntax(syntax: str):
    try:
        syntax = re.sub(r"([+-])", r" \g<1> ", syntax)
        stack = syntax.split()
        params = []

        while len(stack) > 1 and stack[-2] not in ["+", "-"]:
            params.insert(0, stack.pop())

        params.insert(0, stack)

        if len(params) == 1:
            params.append("0")

        if len(params) == 2:
            params.append(None)

        # At this point, the stack contains the following items
        # 0: Pool (list that will be parsed by the standard roll parser)
        # 1: Hunger ("0" or the user's input)
        # 2: Difficulty (None or the user's input)

        # We validate the pool stack later, but we will validate hunger and difficulty
        # here. We don't modify anything; the roll parser will do that for us. Insteat,
        # we simply check for validity.

        if params[1].lower() != "hunger": # "hunger" is a valid option here
            hunger = int(params[1])
            if not 0 <= hunger <= 5:
                raise ValueError("Hunger must be between 0 and 5.")

        difficulty = params[2]
        if difficulty is not None:
            difficulty = int(difficulty)
            if difficulty < 0:
                raise ValueError("Difficulty cannot be less than 0.")

    except Exception as err:
        print(type(err))
        raise SyntaxError from ValueError

    return params
