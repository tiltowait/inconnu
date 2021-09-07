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

    char_name, char_id = common.get_character(ctx.guild.id, ctx.author.id, character)

    if char_name is None:
        err = common.character_options_message(ctx.guild.id, ctx.author.id, character)
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    if not macro_common.is_macro_name_valid(macro_name):
        await common.display_error(
            ctx, char_name, "Macro names may only contain letters and underscores."
        )

    try:
        macro = await macro_common.macro_db.fetch_macro(char_id, macro_name)
        parameters = macro["pool"]
        parameters.append(hunger)
        parameters.append(difficulty)

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
    padding = [0 for _ in range(3 - len(components))]
    components.extend(padding)

    if len(components) > 3:
        raise SyntaxError

    try:
        hunger = int(components[1])
        difficulty = int(components[2])

        if not 0 <= hunger <= 5:
            raise ValueError("Hunger must be between 0 and 5.")

        if difficulty < 0:
            raise ValueError("Difficulty cannot be less than 0.")

        # Parser expects strings
        components[1] = str(hunger)
        components[2] = str(difficulty)

    except ValueError:
        raise SyntaxError from ValueError

    return components
