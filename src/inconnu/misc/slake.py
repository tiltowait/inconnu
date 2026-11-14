"""misc/slake.py - Slake 1 or more Hunger."""

import asyncio
from typing import Any

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

    slaked = min(amount, character.hunger)

    if slaked == 0:
        await ctx.respond(f"**{character.name}** has no Hunger!", ephemeral=True)
    else:
        old_hunger = character.hunger
        character.hunger -= slaked
        character.stat_log.slake += slaked

        if old_hunger >= 4:
            view = ui.views.FrenzyView(character, 3, ctx.user.id)
        else:
            view = None

        update = f"**{character.name}** slaked `{slaked}` Hunger (now at `{character.hunger}`)."

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
