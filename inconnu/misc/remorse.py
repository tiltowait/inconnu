"""misc/remorse.py - Perform a remorse check."""

import random

from .. import common
from .. import character as char
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=remorse-checks"


async def remorse(ctx, character=None):
    """Perform a remorse check on a given character."""
    try:
        tip = "`/remorse` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        # Character obtained
        if character.stains == 0:
            await ctx.respond(f"{character.name} has no stains! No remorse necessary.", hidden=True)
            return

        remorseful = __remorse_roll(character)
        await __display_outcome(ctx, character, remorseful)

    except common.FetchError:
        pass


async def __display_outcome(ctx, character: VChar, remorseful: bool):
    """Process the remorse result and display to the user."""
    title = "Remorse Success" if remorseful else "Remorse Fail"
    if remorseful:
        footer ="You keep the Beast at bay. For now."
    else:
        footer ="The downward spiral continues ..."

    await char.display(ctx, character,
        title=title,
        footer=footer,
        fields=[("Humanity", char.HUMANITY)]
    )


def __remorse_roll(character: VChar) -> bool:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = max(unfilled, 1)
    successful = False

    for _ in range(rolls):
        throw = random.randint(1, 10)
        if throw >= 6:
            successful = True
            break

    if not successful:
        character.humanity -= 1
        character.log("degen")
    else:
        character.stains = 0

    character.log("remorse")

    return successful
