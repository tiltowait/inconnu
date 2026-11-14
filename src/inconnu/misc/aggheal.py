"""misc/aggheal.py - Heal aggravated damage."""

import asyncio
from typing import NamedTuple

import errors
import inconnu
import services
from constants import ROUSE_FAIL_COLOR, Damage
from ctx import AppCtx, AppResponse
from models import VChar
from services.haven import haven
from utils import get_message
from utils.urls import docs_url

__HELP_URL = docs_url("guides/gameplay-shortcuts#aggravated-healing")


class AggHealOutcome(NamedTuple):
    """The outcome of healing Aggravated damage."""

    gain: int
    torpor: bool


def _can_aggheal(character: VChar):
    """Raise an error if the character can't agg heal."""
    if character.aggravated_hp == 0:
        raise errors.CharacterError(f"{character.name} has no Aggravated Health damage!")


@haven(__HELP_URL, _can_aggheal, "None of your characters have Aggravated Health damage.")
async def aggheal(ctx: AppCtx, character: VChar):
    """Heal a point of aggravated damage."""

    if Damage.AGGRAVATED not in character.health:
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

    inter, _ = await asyncio.gather(
        __display_outcome(ctx, character, outcome), character.save_changes()
    )
    msg = await get_message(inter)
    await services.post_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Aggravated Damage Healed",
        message=update_msg,
    )


async def __heal(character: VChar) -> AggHealOutcome:
    """
    Heal agg damage.
    Does not check if the character has agg damage!
    """
    failures = sum(inconnu.d10() < 6 for _ in range(3))
    hunger_gain = failures

    torpor = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        torpor = True

    # Update the character
    character.hunger += hunger_gain
    character.health = Damage.NONE + character.health[:-1]

    if character.is_vampire:
        character.log.record_rouse(3 - failures, failures, hunger_gain)

    return AggHealOutcome(gain=hunger_gain, torpor=torpor)


async def __display_outcome(ctx: AppCtx, character: VChar, outcome: AggHealOutcome) -> AppResponse:
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
