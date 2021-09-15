"""macros/delete.py - Deleting character macros."""

from ..vchar import errors, VChar
from .. import common

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=deletion"


async def process(ctx, macro_name: str, character=None):
    """Delete the given macro."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = f"`/macro delete` `macro:{macro_name}` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return

    try:
        character.delete_macro(macro_name)
        await ctx.respond(
            f"Deleted **{character.name}'s** `{macro_name}` macro.",
            hidden=True
        )

    except errors.MacroNotFoundError as err:
        await common.display_error(ctx, character.name, err, __HELP_URL)
