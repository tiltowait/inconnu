"""misc/aggheal.py - Heal aggravated damage."""

from types import SimpleNamespace

import inconnu
from inconnu.constants import ROUSE_FAIL_COLOR, Damage
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#aggravated-healing"


def _can_aggheal(character):
    """Raise an error if the character can't agg heal."""
    if character.aggravated_hp == 0:
        raise inconnu.errors.CharacterError(f"{character.name} has no Aggravated Health damage!")


@haven(__HELP_URL, _can_aggheal, "None of your characters have Aggravated Health damage.")
async def aggheal(ctx, character):
    """Heal a point of aggravated damage."""

    if character.health.count(Damage.AGGRAVATED) == 0:
        await ctx.respond(f"{character.name} has no aggravated damage to heal!", ephemeral=True)
        return

    outcome = await __heal(character)

    # Build the update message
    update_msg = f"`{character.aggravated_hp}` Aggravated Damage remaining."
    if character.is_vampire:
        update_msg += f"\nGained `{outcome.gain}` Hunger (now at `{character.hunger}`)"
        if outcome.torpor:
            update_msg += " and fell into torpor!"
        else:
            update_msg += "."

    inter = await __display_outcome(ctx, character, outcome)
    msg = await inconnu.get_message(inter)
    await inconnu.common.report_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Aggravated Damage Healed",
        message=update_msg,
    )


async def __heal(character: "VChar"):
    """
    Heal agg damage.
    Does not check if the character has agg damage!
    """
    hunger_gain = 0
    for _ in range(3):
        if inconnu.d10() < 6:
            hunger_gain += 1

    torpor = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        torpor = True

    # Update the character
    character.hunger += hunger_gain
    character.health = Damage.NONE + character.health[:-1]

    if character.is_vampire:
        character.log("rouse", 3)

    await character.commit()
    return SimpleNamespace(gain=hunger_gain, torpor=torpor)


async def __display_outcome(ctx, character, outcome):
    """Display the outcome of the healing."""
    fields = [("Health", inconnu.character.DisplayField.HEALTH)]

    if character.is_vampire:
        gain = "Max Hunger" if character.hunger == 5 else f"Gain {outcome.gain} Hunger"
        color = ROUSE_FAIL_COLOR if (outcome.torpor or outcome.gain) > 0 else None
        title = f"Agg damage healed | {gain}"
        footer = "FALL INTO TORPOR!" if outcome.torpor else None
        fields.append(("Hunger", inconnu.character.DisplayField.HUNGER))
    else:
        title = "Damage healed"
        footer = None
        color = None

    return await inconnu.character.display(
        ctx,
        character,
        title=title,
        footer=footer,
        fields=fields,
        color=color,
    )
