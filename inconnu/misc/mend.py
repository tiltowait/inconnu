"""misc/mend.py - Mend Superficial damage."""

from types import SimpleNamespace

import inconnu
from inconnu.constants import ROUSE_FAIL_COLOR, Damage

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=mending-damage"


async def mend(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/mend` `character:CHARACTER`",
        char_filter=_can_mend,
        errmsg="None of your characters have any damage to mend! Did you mean `/aggheal`?",
        help=__HELP_URL,
    )
    character = await haven.fetch()
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
        msg = await inconnu.get_message(inter)
        await inconnu.common.report_update(
            ctx=ctx, character=character, title="Damage Mended", message=update_msg, msg=msg
        )


def _can_mend(character):
    """Raises an error if the character has no superficial health damage."""
    if character.superficial_hp == 0:
        raise inconnu.errors.CharacterError(f"{character.name} has no damage to mend.")


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

    return await inconnu.character.display(
        ctx, character, title=title, fields=fields, footer=footer, view=view, color=color
    )


async def __heal(character):
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

    await character.commit()
    return SimpleNamespace(mended=mending, rouse=rouse, frenzy=frenzy)
