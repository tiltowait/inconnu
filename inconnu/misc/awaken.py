"""misc/wake.py - Automate the awakening bookkeeping."""

import random

from .. import common
from ..character import update as char_update
from ..constants import ROUSE_FAIL_COLOR

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=awakening"


async def awaken(ctx, character=None):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    try:
        tip = "`/awaken` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        message = "**Awakening:**"
        recovery = []

        # First, heal Superficial Willpower damage
        swp = character.superficial_wp
        recovered = min(swp, character.willpower_recovery)
        recovery.append(f"sw=-{recovered}")
        color = None

        if recovered > 0:
            message += f"\nRecovered **{recovered}** Willpower."

        if character.splat == "vampire":
            rouse_success = random.randint(1, 10) >= 6
            if rouse_success:
                message += "\n**No** Hunger gain."
            else:
                message += "\nRouse failure. "
                color = ROUSE_FAIL_COLOR

                if character.hunger == 5:
                    message += "**Enter torpor!**"
                else:
                    character.hunger += 1
                    message += f"Increase Hunger to **{character.hunger}**."
        else:
            shp = character.superficial_hp
            stamina = character.find_trait("Stamina").rating
            recovered = min(shp, stamina)

            if recovered > 0:
                message += f"\nRecovered **{recovered}** Health."
                recovery.append(f"sh=-{recovered}")


        await char_update(ctx, " ".join(recovery), character, color, message)
        character.log("awaken")
        if character.splat == "vampire":
            character.log("rouse")

    except common.FetchError:
        pass
