"""misc/stain.py - Apply or remove stains from characters."""

import discord

import inconnu
import services
import ui
from ctx import AppCtx, AppResponse
from models import VChar
from services.haven import haven
from utils import get_message
from utils.text import pluralize
from utils.urls import docs_url

__HELP_URL = docs_url("guides/gameplay-shortcuts#applying-stains")


@haven(__HELP_URL)
async def stain(ctx: AppCtx, character: VChar, delta: int, *, player: discord.Member):
    """Apply or remove stains."""
    try:
        if delta == 0:
            raise ValueError("Stain `delta` can't be zero!")

        fields = [("Humanity", inconnu.character.DisplayField.HUMANITY)]
        footer = None

        total_stains = max(0, min(10, character.stains + delta))
        delta = total_stains - character.stains
        if delta == 0:
            # Clamping absorbed the whole change
            if total_stains == 10:
                raise ValueError(f"**{character.name}** already has `10` Stains.")
            raise ValueError(f"**{character.name}** has no Stains to remove.")

        message = None
        if damage := character.add_stains(delta):
            fields.append(("Willpower", inconnu.character.DisplayField.WILLPOWER))
            message = f"\n**Degeneration!** `+{damage}` Aggravated Willpower damage."

        character.log.stains_gained += max(delta, 0)
        if character.degeneration:
            footer = "Degeneration! -2 dice to all rolls. Remains until /remorse or auto-drop."

        title = "Added" if delta > 0 else "Removed"
        title = f"{title} {pluralize(abs(delta), 'Stain')}"

        await character.save_changes()
        inter = await inconnu.character.display(
            ctx, character, title, message=message, owner=player, fields=fields, footer=footer
        )
        await __report(ctx, inter, character, delta)

    except ValueError as err:
        # Delta was 0, or clamping made it 0
        await ui.embeds.error(ctx, err, help=__HELP_URL)


async def __report(
    ctx: AppCtx,
    inter: AppResponse,
    character: VChar,
    delta: int,
):
    """Post the Stain change to the update channel."""
    verbed = "gained" if delta > 0 else "removed"
    delta = abs(delta)
    stains = "Stains" if delta > 1 else "Stain"

    msg = await get_message(inter)

    await services.post_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Stains",
        message=f"**{character.name}** {verbed} `{delta}` {stains}.",
    )
