"""misc/slake.py - Slake 1 or more Hunger."""

from .. import common
from .. import character as char

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
            character.hunger -= slaked
            character.log("slake", slaked)

            await char.display(ctx, character,
                title=f"Slaked {slaked} Hunger",
                fields=[("New Hunger", char.HUNGER)]
            )

    except common.FetchError:
        pass
