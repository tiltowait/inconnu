"""macros/roll.py - Rolling character macros."""

from ..roll import perform_roll, display_outcome
from . import macro_common
from .. import common
from ..databases import MacroNotFoundError

async def process(ctx, syntax: str, character=None):
    """Roll a macro."""
    macro_name = None
    hunger = 0
    difficulty = 0

    try:
        macro_name, hunger, difficulty = __expand_syntax(syntax)
    except SyntaxError:
        err = "**Syntax:** `/vm <macro_name> [hunger] [difficulty]`"
        err += "\n\n `hunger` and `difficulty` are optional."
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    char_name = None
    char_id = None

    try:
        char_name, char_id = macro_common.match_character(ctx.guild.id, ctx.author.id, character)
    except ValueError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    # We have a valid character
    if not macro_common.is_macro_name_valid(macro_name):
        await common.display_error(
            ctx, char_name, "Macro names may only contain letters and underscores."
        )

    try:
        macro = await macro_common.macro_db.fetch_macro(char_id, macro_name)
        parameters = macro["pool"]
        parameters.append(hunger)
        parameters.append(difficulty or macro["diff"])

        results = perform_roll(ctx, char_id, *parameters)
        await display_outcome(ctx, char_name, results, macro["comment"])

    except MacroNotFoundError:
        await common.display_error(ctx, char_name, f"You do not have a macro named `{macro_name}`.")
    except ValueError as err:
        # The user may have deleted a trait, which means the macro is invalid.
        await common.display_error(ctx, char_name or ctx.author.display_name, str(err))


def __expand_syntax(syntax: str):
    """Expands the syntax to fit pool, hunger, diff."""
    components = syntax.split()

    if len(components) == 1:
        components.append(0)
        components.append(None)
    elif len(components) == 2:
        components.append(None)
    elif len(components) > 3:
        raise SyntaxError

    try:
        hunger = int(components[1])

        if not 0 <= hunger <= 5:
            raise ValueError("Hunger must be between 0 and 5.")

        # If the user didn't supply a difficulty, we don't want to override
        # the default difficulty stored in the macro.
        difficulty = components[2]
        if difficulty is not None:
            difficulty = int(difficulty)
            if difficulty < 0:
                raise ValueError("Difficulty cannot be less than 0.")

    except ValueError:
        raise SyntaxError from ValueError

    return components
