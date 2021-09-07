"""macros/delete.py - Deleting character macros."""

from . import macro_common
from ..databases import MacroNotFoundError
from .. import common

async def process(ctx, macro_name: str, character=None):
    """Delete the given macro."""
    char_name = None
    char_id = None

    try:
        char_name, char_id = macro_common.match_character(ctx.guild.id, ctx.author.id, character)
    except ValueError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    # Got a proper character name

    try:
        macro_name = macro_name.upper()
        await macro_common.macro_db.delete_macro(char_id, macro_name)
        await ctx.respond(f"Deleted **{char_name}'s** `{macro_name}` macro.", hidden=True)

    except MacroNotFoundError:
        await common.display_error(ctx, char_name, f"You have no macro named `{macro_name}`.")
