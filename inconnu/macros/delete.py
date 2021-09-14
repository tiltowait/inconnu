"""macros/delete.py - Deleting character macros."""

from ..vchar import errors, VChar
from .. import common

async def process(ctx, macro_name: str, character=None):
    """Delete the given macro."""
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)
        character.delete_macro(macro_name)
        await ctx.respond(
            f"Deleted **{character.name}'s** `{macro_name.upper()}` macro.",
            hidden=True
        )

    except errors.MacroNotFoundError:
        await common.display_error(ctx, character.name, f"You have no macro named `{macro_name}`.")
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return