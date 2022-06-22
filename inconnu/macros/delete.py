"""macros/delete.py - Deleting character macros."""

from .. import common
from ..vchar import errors

__HELP_URL = "https://www.inconnu.app/#/macros?id=deletion"


async def delete(ctx, macro_name: str, character=None):
    """Delete the given macro."""
    try:
        tip = f"`/macro delete` `macro:{macro_name}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        await character.delete_macro(macro_name)
        await ctx.respond(f"Deleted **{character.name}'s** `{macro_name}` macro.", ephemeral=True)

    except errors.MacroNotFoundError as err:
        await common.present_error(ctx, err, character=character.name, help_url=__HELP_URL)
    except common.FetchError:
        pass
