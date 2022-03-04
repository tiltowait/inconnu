"""misc/bol.py - Blush of Life shortcut command."""

import asyncio

from .rouse import rouse
from .. import common

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=blush-of-life"


async def bol(ctx, character):
    """Perform a Blush of Life check based on the character's Humanity."""
    try:
        tip = "`/bol` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if character.humanity == 10:
            await ctx.respond("Blush of Life is unnecessary. You look hale and healthy.")
        elif character.humanity == 9:
            await ctx.respond("Blush of Life is unnecessary. You look somewhat ill but not dead.")
        else:
            await asyncio.gather(
                rouse(ctx, 1, character, "Blush of Life", character.humanity == 8, oblivion=False),
                character.log("blush")
            )

    except common.FetchError:
        pass
