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

    char_convictions = "\n".join(character.convictions) if character.convictions else "*None*"
    embed = inconnu.utils.VCharEmbed(
        ctx,
        character,
        player,
        character_author=True,
        title="Convictions",
        description=char_convictions,
    )
    await inconnu.respond(ctx)(embed=embed, ephemeral=ephemeral)
