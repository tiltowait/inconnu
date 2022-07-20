"""misc/wake.py - Automate the awakening bookkeeping."""

import asyncio

import inconnu

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=awakening"


async def awaken(ctx, character=None):
    """Perform a Rouse check and heal Superficial Willpower damage."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/awaken` `character:CHARACTER`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    message = "**Awakening:**"
    recovery = []

    # First, heal Superficial Willpower damage
    swp = character.superficial_wp
    recovered = min(swp, character.willpower_recovery)
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
            color = inconnu.constants.ROUSE_FAIL_COLOR

            if character.hunger == 5:
                message += "**Enter torpor!**"
            else:
                await character.set_hunger(character.hunger + 1)
                message += f"Increase Hunger to **{character.hunger}**."
    else:
        shp = character.superficial_hp
        stamina = character.find_trait("Stamina").rating
        recovered = min(shp, stamina)

        if recovered > 0:
            message += f"\nRecovered **{recovered}** Health."
            recovery.append(f"sh=-{recovered}")

    await inconnu.character.update(
        ctx,
        parameters=" ".join(recovery),
        character=character,
        color=color,
        update_message=message,
    )

    tasks = [character.log("awaken")]
    if character.is_vampire:
        tasks.append(character.log("rouse"))

    await asyncio.gather(*tasks)
