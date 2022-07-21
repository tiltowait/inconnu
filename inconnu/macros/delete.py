"""macros/delete.py - Deleting character macros."""

import inconnu

from ..vchar import errors

__HELP_URL = "https://www.inconnu.app/#/macros?id=deletion"


async def delete(ctx, macro_name: str, character=None):
    """Delete the given macro."""
    try:
        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            tip=f"`/macro delete` `macro:{macro_name}` `character:CHARACTER`",
            help=__HELP_URL,
        )
        character = await haven.fetch()

        await character.delete_macro(macro_name)
        await ctx.respond(f"Deleted **{character.name}'s** `{macro_name}` macro.", ephemeral=True)

    except errors.MacroNotFoundError as err:
        await inconnu.utils.error(ctx, err, character=character.name, help=__HELP_URL)
