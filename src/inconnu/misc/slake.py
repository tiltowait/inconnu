"""misc/slake.py - Slake 1 or more Hunger."""

import asyncio
from typing import Any, NamedTuple

import errors
import inconnu
import services
import ui
from ctx import AppCtx, AppInvocation
from models import VChar
from services.haven import haven
from utils import get_message
from utils.urls import docs_url

__HELP_URL = docs_url("guides/gameplay-shortcuts#slaking-hunger")
FRENZY_HUNGER = 4  # Slaking from this Hunger or more calls for a frenzy check


class SlakeOutcome(NamedTuple):
    """The outcome of slaking Hunger."""

    slaked: int
    frenzy: bool  # Whether a DC 3 frenzy check is due


def _can_slake(character: VChar):
    """Raises an exception if the character isn't a vampire or is at Hunger 0."""
    if not character.is_vampire:
        raise errors.CharacterError(f"{character.name} isn't a vampire!")
    if character.hunger == 0:
        raise errors.CharacterError(f"{character.name} has no Hunger!")


@haven(__HELP_URL, _can_slake, "None of your characters have Hunger to slake.")
async def slake(ctx: AppCtx, character: VChar, amount: int, **kwargs: Any):
    """Slake a character's Hunger, after finding the character."""
    await perform_slake(ctx, character, amount, **kwargs)


async def perform_slake(ctx: AppInvocation, character: VChar, amount: int, **kwargs: Any):
    """Slake a character's Hunger."""
    if not character.is_vampire:
        await ctx.respond("Only vampires need to slake Hunger!", ephemeral=True)
        return

    if character.hunger == 0:
        await ctx.respond(f"**{character.name}** has no Hunger!", ephemeral=True)
    else:
        slaked, frenzy = slake_hunger(character, amount)
        view = ui.views.FrenzyView(character, 3, ctx.user.id) if frenzy else None
        update = slake_update_message(character, slaked)

        inter = await inconnu.character.display(
            ctx,
            character,
            title=f"Slaked {slaked} Hunger",
            fields=[("New Hunger", inconnu.character.DisplayField.HUNGER)],
            view=view,
            **kwargs,
        )
        msg = await get_message(inter)
        await asyncio.gather(
            character.save_changes(),
            services.post_update(
                ctx=ctx,
                msg=msg,
                character=character,
                title="Hunger Slaked",
                message=update,
            ),
        )


def slake_hunger(character: VChar, amount: int) -> SlakeOutcome:
    """Slake up to amount Hunger, down to 0, and log it. The character must
    be a vampire with Hunger."""
    frenzy = character.hunger >= FRENZY_HUNGER
    slaked = min(amount, character.hunger)
    character.hunger -= slaked
    character.log.hunger_slaked += slaked
    character.log.times_slaked += 1
    return SlakeOutcome(slaked=slaked, frenzy=frenzy)


def slake_update_message(character: VChar, slaked: int) -> str:
    """The update channel's description of a slake."""
    return f"**{character.name}** slaked `{slaked}` Hunger (now at `{character.hunger}`)."
