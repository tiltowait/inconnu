"""misc/wake.py - Automate the awakening bookkeeping."""

import random

from .. import common
from .. import constants
from ..vchar import errors, VChar
from ..character import update

async def process(ctx, character=None):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)

        message = "**Awakening:**"

        # First, heal Superficial Willpower damage
        swp = character.willpower.count(constants.DAMAGE.superficial)
        recovered = min(swp, character.willpower_recovery)

        if recovered > 0:
            message += f"\nRecovered **{recovered}** Willpower."

        rouse_success = random.randint(1, 10) >= 6
        if rouse_success:
            message += "\n**No** Hunger gain."
        else:
            message += "\nRouse failure. "
            if character.hunger == 5:
                message += "**Enter torpor!**"
            else:
                character.hunger += 1
                message += f"Increase Hunger to **{character.hunger}**."

        await update.parse(ctx, f"sw=-{recovered}", character.name, message)

    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
