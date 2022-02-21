"""misc/stain.py - Apply or remove stains from characters."""

from .. import common
from .. import character as char
from ..constants import Damage

__HELP_URL = "https://www.inconnu-bot.com/#/shortcuts?id=applying-stains"


async def stain(ctx, delta, character, owner):
    """Apply or remove stains."""
    try:
        owner = await common.player_lookup(ctx, owner)
        tip = f"`/stain` `delta:{delta}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        fields = [("Humanity", char.DisplayField.HUMANITY)]
        footer = None

        total_stains = character.stains + delta
        delta = total_stains - character.stains

        # Determine degeneration
        if delta > 0 and total_stains > (10 - character.humanity):
            old_overlap = abs(min(10 - character.humanity - character.stains, 0))
            new_overlap = abs(10 - character.humanity - total_stains)
            overlap_delta = new_overlap - old_overlap

            character.apply_damage("willpower", Damage.AGGRAVATED, overlap_delta)
            fields.append(("Willpower", char.DisplayField.WILLPOWER))

            message = f"\n**Degeneration!** `+{overlap_delta}` Aggravated Willpower damage."
        else:
            message = None

        character.stains += delta
        if character.degeneration:
            footer = "Degeneration! -2 dice to all rolls. Remains until /remorse or auto-drop."


        title = "Added" if delta > 0 else "Removed"
        title = f"{title} {common.pluralize(abs(delta), 'Stain')}"

        await char.display(
            ctx, character, title,
            message=message, owner=owner, fields=fields, footer=footer
        )

    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except common.FetchError:
        pass
