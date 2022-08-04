"""misc/bol.py - Blush of Life shortcut command."""

import asyncio

import inconnu

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=blush-of-life"


async def bol(ctx, character):
    """Perform a Blush of Life check based on the character's Humanity."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/bol` `character:CHARACTER`",
        char_filter=_can_blush,
        errmsg="None of your characters need to Blush.",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    if not character.is_vampire:
        await ctx.respond(
            f"**{character.name}** isn't a vampire and doesn't need the Blush of Life!",
            ephemeral=True,
        )
        return

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
        await asyncio.gather(
            inconnu.misc.rouse(
                ctx, 1, character, "Blush of Life", character.humanity == 8, oblivion=False
            ),
            character.set_blush(1),
            character.log("blush"),
        )


def _can_blush(character):
    """Raises an exception if the character isn't capable of Blushing."""
    if not character.is_vampire:
        raise inconnu.errors.CharacterError(f"{character.name} isn't a vampire!")
