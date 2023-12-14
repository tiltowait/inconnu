"""misc/bol.py - Blush of Life shortcut command."""

import inconnu
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#blush-of-life"


def _can_blush(character):
    """Raises an exception if the character isn't capable of Blushing."""
    if not character.is_vampire:
        raise inconnu.errors.CharacterError(f"{character.name} isn't a vampire!")


@haven(__HELP_URL, _can_blush, "None of your characters need to Blush.")
async def bol(ctx, character, ministry_alt):
    """Perform a Blush of Life check based on the character's Humanity."""
    if character.is_thin_blood:
        # Thin-Bloods don't need to Blush. Their appearance depends on Humanity
        effective_humanity = max(9, character.humanity)
    else:
        effective_humanity = character.humanity

    if effective_humanity == 10:
        await ctx.respond(
            f"Blush of Life is unnecessary. **{character.name}** looks hale and healthy."
        )
    elif effective_humanity == 9:
        await ctx.respond(
            f"Blush of Life is unnecessary. **{character.name}** only looks a little sick."
        )
    else:
        msg = "Blush of Life"
        if ministry_alt:
            msg += " - Cold-Blooded bane"
            count = character.bane_severity
        else:
            count = 1

        character.set_blush(1)
        character.log("blush")
        await inconnu.misc.rouse(
            ctx, character, count, msg, character.humanity == 8, oblivion=False
        )
        await character.commit()
