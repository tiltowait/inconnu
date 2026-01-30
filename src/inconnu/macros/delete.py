"""macros/delete.py - Deleting character macros."""

import errors
import ui
from ctx import AppCtx
from models import VChar
from services.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/macros/deletion"


@haven(__HELP_URL)
async def delete(
    ctx: AppCtx,
    character: VChar,
    macro_name: str,
):
    """Delete the given macro."""
    try:
        character.delete_macro(macro_name)
        await ctx.respond(f"Deleted **{character.name}'s** `{macro_name}` macro.", ephemeral=True)
        await character.save()

    except errors.MacroNotFoundError as err:
        await ui.embeds.error(ctx, err, character=character.name, help=__HELP_URL)
