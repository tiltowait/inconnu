"""misc/stain.py - Apply or remove stains from characters."""

import inconnu
from inconnu.constants import Damage
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#applying-stains"


@haven(__HELP_URL)
async def stain(ctx, character, delta, *, player):
    """Apply or remove stains."""
    try:
        if delta == 0:
            raise ValueError("Stain `delta` can't be zero!")

        fields = [("Humanity", inconnu.character.DisplayField.HUMANITY)]
        footer = None

        total_stains = max(0, min(10, character.stains + delta))
        delta = total_stains - character.stains

        # Determine degeneration
        if delta > 0 and total_stains > (10 - character.humanity):
            old_overlap = abs(min(10 - character.humanity - character.stains, 0))
            new_overlap = abs(10 - character.humanity - total_stains)
            overlap_delta = new_overlap - old_overlap

            character.apply_damage("willpower", Damage.AGGRAVATED, overlap_delta)
            fields.append(("Willpower", inconnu.character.DisplayField.WILLPOWER))

            message = f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."
        else:
            message = None

        character.stains += delta
        character.log("stains", delta)
        if character.degeneration:
            footer = "Degeneration! -2 dice to all rolls. Remains until /remorse or auto-drop."

        title = "Added" if delta > 0 else "Removed"
        title = f"{title} {inconnu.common.pluralize(abs(delta), 'Stain')}"

        inter = await inconnu.character.display(
            ctx, character, title, message=message, owner=player, fields=fields, footer=footer
        )
        await __report(ctx, inter, character, delta)
        await character.commit()

    except ValueError as err:
        # Delta was 0
        await inconnu.utils.error(ctx, err, help=__HELP_URL)


async def __report(ctx, inter, character, delta):
    verbed = "gained" if delta > 0 else "removed"
    delta = abs(delta)
    stains = "Stains" if delta > 1 else "Stain"

    msg = await inconnu.get_message(inter)

    await inconnu.common.report_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Stains",
        message=f"**{character.name}** {verbed} `{delta}` {stains}.",
    )
