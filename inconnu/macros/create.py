"""macros/create.py - Creating user macros."""

import re

from . import macro_common
from .. import common
from ..vchar import VChar, errors

async def process(ctx, name: str, pool: str, difficulty=0, comment=None, character=None):
    """Create a macro if the syntax is valid."""
    if difficulty < 0:
        await common.display_error(
            ctx, ctx.author.display_name, "`Difficulty` cannot be less than 0."
        )
        return

    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
    except errors.UnspecifiedCharacterError as err:
        tip = "`/macro create` `name:NAME` `pool:POOL` `character:CHARACTER`"
        character = await common.select_character(ctx, err, ("Minimal syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    if not macro_common.is_macro_name_valid(name):
        await common.display_error(
            ctx, character.name, "Macro names can only contain letters and underscores."
        )
        return

    try:
        pool = __expand_syntax(character, pool)
        character.add_macro(name, pool, difficulty, comment)
        await ctx.respond(f"**{character.name}:** Created macro `{name}`.", hidden=True)

    except (
        SyntaxError, errors.AmbiguousTraitError, errors.TraitNotFoundError,
        errors.MacroAlreadyExistsError
    ) as err:
        await common.display_error(ctx, character.name, err)


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
