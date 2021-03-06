"""character/convictions.py - View or edit character convictions."""

import inconnu

__HELP_URL = "https://www.inconnu.app/"


async def convictions_set(ctx, character):
    """Edit character Convictions."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/character convictions set` `character:CHARACTER`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    modal = inconnu.views.ConvictionsModal(character)
    await ctx.send_modal(modal)


async def convictions_show(ctx, character, player, ephemeral):
    """Show a character's Convictions."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        owner=player,
        tip="`/character convictions show` `character:CHARACTER`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    char_convictions = character.convictions
    char_convictions = "\n".join(char_convictions) if char_convictions else "*None*"

    await inconnu.respond(ctx)(
        f"**{character.name}'s Convictions**\n\n{char_convictions}", ephemeral=ephemeral
    )
