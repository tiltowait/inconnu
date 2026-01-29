"""misc/remorse.py - Perform a remorse check."""

from types import SimpleNamespace as SN

import errors
import inconnu
import services
from models import VChar
from services import haven

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#remorse-checks"


def _can_remorse(character):
    """Raise an exception if we have no stains."""
    if character.stains == 0:
        raise errors.CharacterError(f"{character.name} has no stains.")


@haven(__HELP_URL, _can_remorse, "None of your characters have any stains!")
async def remorse(ctx, character, minimum=1, lasombra_alt=False):
    """Perform a remorse check on a given character."""
    if character.stains == 0:
        await ctx.respond(f"{character.name} has no stains! No remorse necessary.", ephemeral=True)
        return

    outcome = __remorse_roll(character, minimum, lasombra_alt)
    inter = await __display_outcome(ctx, character, outcome)
    await __report(ctx, inter, character, outcome.remorseful)
    await character.save()


async def __display_outcome(ctx, character: VChar, outcome):
    """Process the remorse result and display to the user."""
    title = "Remorse Success" if outcome.remorseful else "Remorse Fail"
    if outcome.remorseful:
        footer = "You keep the Beast at bay. For now."
        color = 0x7777FF
    else:
        footer = "The downward spiral continues ..."
        color = 0x5C0700

    if outcome.lasombra_alt:
        footer += f"\nLasombra alt bane: -{character.bane_severity} dice"

    if outcome.overrode:
        dice = inconnu.utils.pluralize(outcome.minimum, "die")
        footer += f"\nOverride: Rolled {dice} instead of {outcome.nominal}"

    footer += "\nDice: " + ", ".join(map(str, outcome.dice))

    return await inconnu.character.display(
        ctx,
        character,
        title=title,
        footer=footer,
        color=color,
        fields=[("Humanity", inconnu.character.DisplayField.HUMANITY)],
    )


def __remorse_roll(character: VChar, minimum: int, lasombra_alt: bool) -> SN:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = max(unfilled, minimum)
    if lasombra_alt:
        rolls = max(1, rolls - character.bane_severity)
    overrode = unfilled < minimum and minimum > 1
    nominal = unfilled if unfilled > 0 else 1
    successful = False

    dice = []
    for _ in range(rolls):
        throw = inconnu.d10()
        dice.append(throw)
        if throw >= 6:
            successful = True

    if not successful:
        character.humanity -= 1
        character.log("degen")
    else:
        character.stains = 0

    character.log("remorse")

    return SN(
        remorseful=successful,
        minimum=minimum,
        dice=dice,
        overrode=overrode,
        nominal=nominal,
        lasombra_alt=lasombra_alt,
    )


async def __report(ctx, inter, character, remorseful):
    """Generate the task to display the remorse outcome for the update channel."""
    if remorseful:
        verbed = "passed"
        humanity_str = f"Humanity remains at `{character.humanity}`."
    else:
        verbed = "failed"
        humanity_str = f"Humanity drops to `{character.humanity}`."

    msg = await inconnu.get_message(inter)
    await services.character_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Remorse Success" if remorseful else "Remorse Failure",
        message=f"**{character.name}** {verbed} a Remorse test.\n{humanity_str}",
        color=0x5E005E if not remorseful else None,
    )
