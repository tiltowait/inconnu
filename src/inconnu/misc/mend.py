"""misc/mend.py - Mend Superficial damage."""

from typing import NamedTuple

import errors
import inconnu
import services
import ui
from ctx import AppCtx
from inconnu.constants import ROUSE_FAIL_COLOR, Damage
from models import VChar
from services import haven
from utils import get_message

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#mending-damage"


class MendOutcome(NamedTuple):
    mended: int
    rouse: bool
    frenzy: bool


def _can_mend(character: VChar):
    """Raises an error if the character has no superficial health damage."""
    if character.superficial_hp == 0:
        raise errors.CharacterError(f"{character.name} has no damage to mend.")


@haven(
    __HELP_URL,
    _can_mend,
    "None of your characters have any damage to mend! Did you mean `/aggheal`?",
)
async def mend(ctx: AppCtx, character: VChar):
    """Mend damage on a character OR the user's only character."""
    outcome = await __heal(character)

    if isinstance(outcome, str):
        await ctx.respond(outcome, ephemeral=True)
    else:
        # Build the update message
        update_msg = f"Mended `{outcome.mended}` Superficial Damage.\n"
        update_msg += f"`{character.superficial_hp}` remaining."

        if character.is_vampire:
            if outcome.rouse:
                update_msg += " No Hunger gain."
            else:
                update_msg += f" Gained `1` Hunger (now at `{character.hunger}`)."

        if outcome.frenzy:
            update_msg += "\nMust make a frenzy check at DC 4."

        inter = await __display_outcome(ctx, character, outcome)
        msg = await get_message(inter)
        await services.character_update(
            ctx=ctx, character=character, title="Damage Mended", message=update_msg, msg=msg
        )


async def __display_outcome(ctx: AppCtx, character: VChar, outcome: MendOutcome):
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
            view = ui.views.FrenzyView(character, 4, ctx.user.id)

    return await inconnu.character.display(
        ctx, character, title=title, fields=fields, footer=footer, view=view, color=color
    )


async def __heal(character: VChar) -> MendOutcome | str:
    """Heal the character and perform the Rouse check."""
    superficial = character.superficial_hp
    if superficial == 0:
        return f"**{character.name}** has no Superficial damage to mend!"

    mending = min(character.mend_amount, superficial)
    superficial -= mending
    aggravated = character.aggravated_hp
    unhurt = len(character.health) - superficial - aggravated

    track = Damage.NONE * unhurt + Damage.SUPERFICIAL * superficial + Damage.AGGRAVATED * aggravated
    character.health = track

    rouse = inconnu.d10() >= 6
    if not rouse:
        frenzy = character.hunger == 5
        character.hunger += 1
    else:
        frenzy = False

    if character.is_vampire:
        character.log("rouse")

    await character.save()
    return MendOutcome(mended=mending, rouse=rouse, frenzy=frenzy)
