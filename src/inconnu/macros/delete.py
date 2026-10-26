"""macros/delete.py - Deleting character macros."""

import errors
import ui
from ctx import AppCtx
from models import VChar
from services.haven import haven
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/macros#macro-delete")


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
