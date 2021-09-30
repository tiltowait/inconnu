"""misc/mend.py - Mend Superficial damage."""

import random
from types import SimpleNamespace

from .. import common
from ..constants import DAMAGE
from .. import character as char

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=mending-damage"


async def mend(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    try:
        tip = "`/mend` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        outcome = __heal(character)

        if isinstance(outcome, str):
            await ctx.respond(outcome, hidden=True)
        else:
            await __display_outcome(ctx, character, outcome)

    except common.FetchError:
        pass

async def __display_outcome(ctx, character, outcome):
    """Display the results of the mend."""
    title = f"Mended {outcome.mended} damage"
    fields = [("Health", char.HEALTH)]

    if character.splat == "vampire":
        success_text = "Success" if outcome.rouse else "Failure"
        title += f" | Rouse {success_text}"
        fields.append(("Hunger", char.HUNGER))
        footer = "ROLL FOR HUNGER FRENZY" if outcome.frenzy else None
    else:
        footer = None

    await char.display(ctx, character,
        title=title,
        fields=fields,
        footer=footer
    )


def __heal(character):
    """Heal the character and perform the Rouse check."""
    superficial = character.health.count(DAMAGE.superficial)
    if superficial == 0:
        return f"**{character.name}** has no Superficial damage to mend!"

    mending = min(character.mend_amount, superficial)
    superficial -= mending
    aggravated = character.health.count(DAMAGE.aggravated)
    unhurt = len(character.health) - superficial - aggravated

    track = DAMAGE.none * unhurt + DAMAGE.superficial * superficial + DAMAGE.aggravated * aggravated
    character.health = track

    rouse = random.randint(1, 10) >= 6
    if not rouse:
        frenzy = character.hunger == 5
        character.hunger += 1
    else:
        frenzy = False

    if character.splat == "vampire":
        character.log("rouse")
    return SimpleNamespace(mended=mending, rouse=rouse, frenzy=frenzy)
