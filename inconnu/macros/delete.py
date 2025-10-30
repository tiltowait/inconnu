"""macros/delete.py - Deleting character macros."""

import inconnu
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/macros/deletion"


@haven(__HELP_URL)
async def delete(ctx, character, macro_name: str):
    """Delete the given macro."""
    try:
        character.delete_macro(macro_name)
        await ctx.respond(f"Deleted **{character.name}'s** `{macro_name}` macro.", ephemeral=True)
        await character.commit()

    except inconnu.errors.MacroNotFoundError as err:
        await inconnu.embeds.error(ctx, err, character=character.name, help=__HELP_URL)
