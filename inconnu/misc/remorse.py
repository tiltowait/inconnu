"""misc/remorse.py - Perform a remorse check."""

import random
from types import SimpleNamespace as SN

from .. import common
from .. import character as char
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=remorse-checks"


async def remorse(ctx, character=None, minimum=1):
    """Perform a remorse check on a given character."""
    try:
        tip = "`/remorse` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        # Character obtained
        if character.stains == 0:
            await ctx.respond(f"{character.name} has no stains! No remorse necessary.", hidden=True)
            return

        outcome = __remorse_roll(character, minimum)
        await __display_outcome(ctx, character, outcome)

    except common.FetchError:
        pass


async def __display_outcome(ctx, character: VChar, outcome):
    """Process the remorse result and display to the user."""
    title = "Remorse Success" if outcome.remorseful else "Remorse Fail"
    if outcome.remorseful:
        footer = "You keep the Beast at bay. For now."
        color = 0x7777ff
    else:
        footer = "The downward spiral continues ..."
        color = 0x5c0700

    footer += "\nDice: " + ", ".join(map(str, outcome.dice))

    if outcome.overrode:
        dice = common.pluralize(outcome.minimum, 'die')
        footer += f"\nOverride: Rolled {dice} instead of {outcome.nominal}"

    await char.display(ctx, character,
        title=title,
        footer=footer,
        color=color,
        fields=[("Humanity", char.HUMANITY)]
    )


def __remorse_roll(character: VChar, minimum: int) -> SN:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = max(unfilled, minimum)
    overrode = unfilled < minimum and minimum > 1
    nominal = unfilled if unfilled > 0 else 1
    successful = False

    dice = []
    for _ in range(rolls):
        throw = random.randint(1, 10)
        dice.append(throw)
        if throw >= 6:
            successful = True

    if not successful:
        character.humanity -= 1
        character.log("degen")
    else:
        character.stains = 0

    character.log("remorse")

    return SN(remorseful=successful, minimum=minimum, dice=dice, overrode=overrode, nominal=nominal)
