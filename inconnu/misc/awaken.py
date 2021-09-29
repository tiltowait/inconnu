"""misc/wake.py - Automate the awakening bookkeeping."""

import random

from .. import common
from .. import constants
from ..character import update as char_update

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=awakening"


async def awaken(ctx, character=None):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    try:
        tip = "`/awaken` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        message = "**Awakening:**"

        # First, heal Superficial Willpower damage
        swp = character.willpower.count(constants.DAMAGE.superficial)
        recovered = min(swp, character.willpower_recovery)

        if recovered > 0:
            message += f"\nRecovered **{recovered}** Willpower."

        if character.splat == "vampire":
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

        await char_update(ctx, f"sw=-{recovered}", character.name, message)
        character.log("awaken")

    except common.FetchError:
        pass
