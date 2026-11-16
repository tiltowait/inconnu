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
    dice: list[int]  # The three Rouse dice, for vampires


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

    outcome = heal_aggravated(character)

    inter, _ = await asyncio.gather(
        __display_outcome(ctx, character, outcome), character.save_changes()
    )
    msg = await get_message(inter)
    await services.post_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Aggravated Damage Healed",
        message=aggheal_update_message(character, outcome),
    )


def aggheal_update_message(character: VChar, outcome: AggHealOutcome) -> str:
    """The update channel's summary of healing Aggravated damage."""
    update_msg = f"`{character.aggravated_hp}` Aggravated Damage remaining."
    if character.is_vampire:
        update_msg += f"\nGained `{outcome.gain}` Hunger (now at `{character.hunger}`)"
        if outcome.torpor:
            update_msg += " and fell into torpor!"
        else:
            update_msg += "."
    return update_msg


def heal_aggravated(character: VChar) -> AggHealOutcome:
    """Heal one Aggravated Health damage, with three Rouse Checks for
    vampires, and log it. Doesn't save. The caller checks there's damage."""
    dice = [inconnu.d10() for _ in range(3)] if character.is_vampire else []
    failures = sum(die < 6 for die in dice)
    hunger_gain = failures

    torpor = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        torpor = True

    # Update the character
    character.hunger += hunger_gain
    character.health = Damage.NONE + character.health[:-1]

    character.log.times_mended += 1
    if character.is_vampire:
        character.log.record_rouse(3 - failures, failures, hunger_gain)

    return AggHealOutcome(gain=hunger_gain, torpor=torpor, dice=dice)


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
