"""macros/create.py - Creating user macros."""
# pylint: disable=too-many-arguments

import re

from . import macro_common
from .. import common
from ..vchar import VChar, errors

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=creation"


async def create(
    ctx,
    name: str,
    pool: str,
    hunger: bool,
    difficulty: int,
    rouses: int,
    reroll_rouses: bool,
    comment: str,
    character: str
):
    """Create a macro if the syntax is valid."""
    if difficulty < 0:
        await common.present_error(ctx, "`Difficulty` cannot be less than 0.", help_url=__HELP_URL)
        return

    try:
        tip = "`/macro create` `name:NAME` `pool:POOL` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if not macro_common.is_macro_name_valid(name):
            await common.present_error(
                ctx,
                "Macro names can only contain letters and underscores.",
                character=character.name,
                help_url=__HELP_URL
            )
            return

        pool = __expand_syntax(character, pool)
        character.add_macro(name, pool, hunger, rouses, reroll_rouses, difficulty, comment)
        await ctx.respond(f"**{character.name}:** Created macro `{name}`.", hidden=True)

    except (
        SyntaxError, errors.AmbiguousTraitError, errors.TraitNotFoundError,
        errors.MacroAlreadyExistsError
    ) as err:
        await common.present_error(ctx, err, help_url=__HELP_URL, character=character.name)
    except common.FetchError:
        pass


def __expand_syntax(character: VChar, syntax: str):
    """Validates the pool syntax and replaces elements with full trait names."""
    syntax = re.sub(r"([+-])", r" \g<1> ", syntax) # Make sure there are spaces around all operators
    raw_stack = syntax.split()
    final_stack = []

    expecting_operand = True

    for element in raw_stack:
        if expecting_operand:
            # Expecting a number or a trait
            if element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            if element.isdigit():
                final_stack.append(int(element))
            else:
                trait = character.find_trait(element)
                final_stack.append(trait.name)

            expecting_operand = False
        else:
            # Expecting an operator
            if not element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            final_stack.append(element)
            expecting_operand = True

    return final_stack
