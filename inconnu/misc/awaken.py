"""misc/wake.py - Automate the awakening bookkeeping."""

import random

from .. import common
from .. import constants
from ..vchar import errors, VChar
from ..character import update

async def process(ctx, character=None):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = "`/awaken` `character:CHARACTER`"
        character = await common.select_character(ctx, err, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return

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
    character.log("awaken")
