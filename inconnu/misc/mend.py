"""misc/mend.py - Mend Superficial damage."""

import random

from .. import common
from .. import constants
from ..character import update as char_update

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=mending-damage"


async def mend(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    try:
        tip = "`/mend` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if character.hunger == 5:
            await ctx.respond(f"Can't mend. **{character.name}'s** Hunger is at 5!", hidden=True)
        else:
            superficial = character.health.count(constants.DAMAGE.superficial)
            if superficial == 0:
                await ctx.respond("No damage to mend!", hidden=True)
                return

            mending = min(superficial, character.mend_amount)
            update_string = f"sh=-{mending}"
            update_message = f"Mending **{mending}** damage."

            if random.randint(1, 10) < 6:
                update_string += " hunger=+1"
                update_message += " Hunger increased by **1**."

            await char_update(ctx, update_string, character.name, update_message)

    except common.FetchError:
        pass
