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

        if not character.is_vampire:
            await ctx.respond(
                f"**{character.name}** isn't a vampire and doesn't need the Blush of Life!",
                ephemeral=True
            )
            return

        if character.humanity == 10:
            await ctx.respond(
                f"Blush of Life is unnecessary. **{character.name}** looks hale and healthy."
            )
        elif character.humanity == 9:
            await ctx.respond(
                f"Blush of Life is unnecessary. **{character.name}** only looks a little sick."
            )
        else:
            await asyncio.gather(
                rouse(ctx, 1, character, "Blush of Life", character.humanity == 8, oblivion=False),
                character.log("blush")
            )

    except common.FetchError:
        pass
