"""misc/mend.py - Mend Superficial damage."""

import random
from types import SimpleNamespace

import inconnu
from inconnu.constants import Damage, ROUSE_FAIL_COLOR

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=mending-damage"


async def mend(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    try:
        tip = "`/mend` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)
        outcome = __heal(character)

        if isinstance(outcome, str):
            await ctx.respond(outcome, ephemeral=True)
        else:
            await __display_outcome(ctx, character, outcome)

    except inconnu.common.FetchError:
        pass

async def __display_outcome(ctx, character, outcome):
    """Display the results of the mend."""
    title = f"Mended {outcome.mended} damage"
    fields = [("Health", inconnu.character.DisplayField.HEALTH)]

    footer = None
    color = None
    view = None

    if character.is_vampire:
        if outcome.rouse:
            success_text = "Success" if outcome.rouse else "Failure"
        else:
            success_text = "Failure"
            color = ROUSE_FAIL_COLOR

        title += f" | Rouse {success_text}"
        fields.append(("Hunger", inconnu.character.DisplayField.HUNGER))

        if outcome.frenzy:
            footer = "Rouse failure at Hunger 5!"
            view = inconnu.views.FrenzyView(character, 4)

    await inconnu.character.display(ctx, character,
        title=title,
        fields=fields,
        footer=footer,
        view=view,
        color=color
    )


def __heal(character):
    """Heal the character and perform the Rouse check."""
    superficial = character.health.count(Damage.SUPERFICIAL)
    if superficial == 0:
        return f"**{character.name}** has no Superficial damage to mend!"

    mending = min(character.mend_amount, superficial)
    superficial -= mending
    aggravated = character.health.count(Damage.AGGRAVATED)
    unhurt = len(character.health) - superficial - aggravated

    track = Damage.NONE * unhurt + Damage.SUPERFICIAL * superficial + Damage.AGGRAVATED * aggravated
    character.health = track

    rouse = random.randint(1, 10) >= 6
    if not rouse:
        frenzy = character.hunger == 5
        character.hunger += 1
    else:
        frenzy = False

    if character.is_vampire:
        character.log("rouse")
    return SimpleNamespace(mended=mending, rouse=rouse, frenzy=frenzy)
