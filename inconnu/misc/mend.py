"""misc/mend.py - Mend Superficial damage."""

import random

from .. import common
from .. import constants
from ..character.update import parse as update
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=mending-damage"


async def process(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = "`/mend` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return

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

        await update(ctx, update_string, character.name, update_message)
