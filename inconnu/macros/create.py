"""macros/create.py - Creating user macros."""

import re

from . import macro_common
from .. import common
from ..constants import character_db
from ..databases import AmbiguousTraitError, TraitNotFoundError, MacroAlreadyExistsError

async def process(ctx, name: str, pool: str, difficulty=0, comment=None, character=None):
    """Create a macro if the syntax is valid."""
    if difficulty < 0:
        await common.display_error(
            ctx, ctx.author.display_name, "`Difficulty` cannot be less than 0."
        )
        return

    char_name, char_id = common.get_character(ctx.guild.id, ctx.author.id, character)
    if char_id is None:
        await ctx.respond(f"You don't have a character named {character}.", hidden=True)
        return

    if not macro_common.is_macro_name_valid(name):
        await common.display_error(
            ctx, char_name, "Macro names can only contain letters and underscores."
        )
        return

    try:
        pool = __expand_syntax(ctx.guild.id, ctx.author.id, char_id, pool)

        await macro_common.macro_db.create_macro(char_id, name, pool, difficulty, comment)

        await ctx.respond(f"Macro `{name}` created.", hidden=True)

    except (SyntaxError, AmbiguousTraitError, TraitNotFoundError, MacroAlreadyExistsError) as err:
        await common.display_error(ctx, char_name, err)


def __expand_syntax(guildid: int, userid: int, char_id: int, syntax):
    """Validates the pool syntax and replaces elements with full trait names."""
    syntax = re.sub(r"([+-])", r" \g<1> ", syntax) # Make sure there are spaces around all operators
    raw_stack = syntax.split()
    final_stack = []

    last_element_was_operator = True

    for element in raw_stack:
        if last_element_was_operator:
            # Expecting a number or a trait
            if element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            if element.isdigit():
                final_stack.append(int(element))
            else:
                trait, _ = character_db.trait_rating(guildid, userid, char_id, element)
                final_stack.append(trait)

            last_element_was_operator = False
        else:
            # Expecting an operator
            if not element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            final_stack.append(element)
            last_element_was_operator = True

    return final_stack
