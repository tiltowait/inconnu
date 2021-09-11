"""misc/slake.py - Slake 1 or more Hunger."""

from .. import common
from ..character import update
from ..vchar import errors, VChar

async def process(ctx, amount, character=None):
    """Slake a character's Hunger."""
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)
        slaked = min(amount, character.hunger)

        if slaked == 0:
            await ctx.respond(f"**{character.name}** has no Hunger!", hidden=True)
        else:
            await update.parse(
                ctx,
                f"hunger=-{slaked}",
                character.name,
                f"Slaked **{slaked}** Hunger."
            )

    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
