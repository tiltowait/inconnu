"""misc/awake.py - Automate the awakening bookkeeping."""

import discord
from loguru import logger

import constants
import inconnu
from ctx import AppCtx
from models import VChar
from services.haven import haven
from utils.urls import docs_url

__HELP_URL = docs_url("guides/gameplay-shortcuts#awakening")


@haven(__HELP_URL)
async def awaken(ctx: AppCtx, character: VChar):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    message = "**Awakening:**"
    recovery = []

    # First, heal Superficial Willpower damage
    recovered = min(character.superficial_wp, character.willpower_recovery)
    recovery.append(f"sw=-{recovered}")
    color = None

    if recovered > 0:
        message += f"\nRecovered **{recovered}** Willpower."

    if character.is_vampire:
        rouse_success = inconnu.d10() >= 6
        if rouse_success:
            message += "\n**No** Hunger gain."
        else:
            message += "\nRouse failure. "
            color = discord.Color(constants.ROUSE_FAIL_COLOR)

            if character.hunger == 5:
                message += "**Enter torpor!**"
            else:
                character.hunger += 1
                message += f"Increase Hunger to **{character.hunger}**."
    else:
        stamina = character.find_trait("Stamina").rating
        if character.is_ghoul:
            stamina *= 2
        recovered = min(character.superficial_hp, stamina)

        if recovered > 0:
            message += f"\nRecovered **{recovered}** Health."
            recovery.append(f"sh=-{recovered}")

    character.log("awaken")

    # If a vampire awakens, we want to turn off its blush. N/A (-1, set at
    # Humanity 9+) is left alone.
    if character.is_vampire and not character.is_thin_blood and character.header.blush == 1:
        logger.debug("AWAKEN: {} is no longer Blushed", character.name)
        character.set_blush(0)
    else:
        logger.debug("AWAKEN: {} isn't Blushed; header unchanged", character.name)

    if character.is_vampire:
        character.log("rouse")

    # The update function will commit for us
    await inconnu.character.update(
        ctx,
        parameters=" ".join(recovery),
        character=character,
        color=color,
        update_message=message,
    )
