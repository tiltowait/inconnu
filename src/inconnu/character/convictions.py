"""character/convictions.py - View or edit character convictions."""

import inconnu
from services import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/profiles#convictions"


@haven(__HELP_URL)
async def convictions_set(ctx, character):
    """Edit character Convictions."""
    modal = inconnu.views.ConvictionsModal(character)
    await ctx.send_modal(modal)


@haven(__HELP_URL)
async def convictions_show(ctx, character, player, ephemeral):
    """Show a character's Convictions."""
    char_convictions = "\n".join(character.convictions) if character.convictions else "*None*"
    embed = inconnu.embeds.VCharEmbed(
        ctx,
        character,
        player,
        link=True,
        title="Convictions",
        description=char_convictions,
    )
    await ctx.respond(embed=embed, ephemeral=ephemeral)
