"""macros/delete.py - Deleting character macros."""

import inconnu

__HELP_URL = "https://docs.inconnu.app/command-reference/macros/deletion"


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

        character.delete_macro(macro_name)
        await ctx.respond(f"Deleted **{character.name}'s** `{macro_name}` macro.", ephemeral=True)
        await character.commit()

    except inconnu.errors.MacroNotFoundError as err:
        await inconnu.utils.error(ctx, err, character=character.name, help=__HELP_URL)
