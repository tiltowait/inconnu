"""misc/stain.py - Apply or remove stains from characters."""

import inconnu
from inconnu.constants import Damage

__HELP_URL = "https://www.inconnu.app/#/shortcuts?id=applying-stains"


async def stain(ctx, delta, character, owner):
    """Apply or remove stains."""
    try:
        if delta == 0:
            raise ValueError("Stain `delta` can't be zero!")

        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            owner=owner,
            tip=f"`/stain` `delta:{delta}` `character:CHARACTER`",
            help=__HELP_URL,
        )
        character = await haven.fetch()

        fields = [("Humanity", inconnu.character.DisplayField.HUMANITY)]
        footer = None

        total_stains = character.stains + delta
        delta = total_stains - character.stains

        # Determine degeneration
        if delta > 0 and total_stains > (10 - character.humanity):
            old_overlap = abs(min(10 - character.humanity - character.stains, 0))
            new_overlap = abs(10 - character.humanity - total_stains)
            overlap_delta = new_overlap - old_overlap

            await character.apply_damage("willpower", Damage.AGGRAVATED, overlap_delta)
            fields.append(("Willpower", inconnu.character.DisplayField.WILLPOWER))

            message = f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."
        else:
            message = None

        await character.set_stains(character.stains + delta)
        if character.degeneration:
            footer = "Degeneration! -2 dice to all rolls. Remains until /remorse or auto-drop."

        title = "Added" if delta > 0 else "Removed"
        title = f"{title} {inconnu.common.pluralize(abs(delta), 'Stain')}"

        inter = await inconnu.character.display(
            ctx, character, title, message=message, owner=haven.owner, fields=fields, footer=footer
        )
        await __report(ctx, inter, character, delta)

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
