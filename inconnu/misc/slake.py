"""misc/slake.py - Slake 1 or more Hunger."""

from .. import common
from ..character import update as char_update

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=slaking-hunger"


async def slake(ctx, amount, character=None):
    """Slake a character's Hunger."""
    try:
        tip = f"`/slake` `amount:{amount}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        slaked = min(amount, character.hunger)

        if slaked == 0:
            await ctx.respond(f"**{character.name}** has no Hunger!", hidden=True)
        else:
            await char_update(
                ctx,
                f"hunger=-{slaked}",
                character.name,
                f"Slaked **{slaked}** Hunger."
            )
            character.log("slake", slaked)

    except common.FetchError:
        pass
