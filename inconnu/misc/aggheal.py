"""misc/aggheal.py - Heal aggravated damage."""

import random
from types import SimpleNamespace

from .. import common
from .. import character as char
from ..constants import DAMAGE
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/"


async def aggheal(ctx, character: str):
    """Heal a point of aggravated damage."""
    try:
        tip = "`/aggheal` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if character.health.count(DAMAGE.aggravated) == 0:
            await ctx.respond(f"{character.name} has no aggravated damage to heal!", hidden=True)
            return

        outcome = __heal(character)
        await __display_outcome(ctx, character, outcome)

    except common.FetchError:
        pass


def __heal(character: VChar):
    """
    Heal agg damage.
    Does not check if the character has agg damage!
    """
    hunger_gain = 0
    for _ in range(3):
        if random.randint(1, 10) < 6:
            hunger_gain += 1

    torpor = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        torpor = True


    # Update the character
    character.hunger += hunger_gain
    character.health = DAMAGE.none + character.health[:-1]

    return SimpleNamespace(gain=hunger_gain, torpor=torpor)


async def __display_outcome(ctx, character, outcome):
    """Display the outcome of the healing."""
    gain = "Max Hunger" if character.hunger == 5 else f"Gain {outcome.gain} Hunger"
    title = f"Damage healed | {gain}"
    footer = "FALL INTO TORPOR!" if outcome.torpor else None

    await char.display(ctx, character,
        title=title,
        footer=footer,
        fields=[("Health", char.HEALTH), ("Hunger", char.HUNGER)]
    )
