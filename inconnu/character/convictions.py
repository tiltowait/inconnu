"""character/convictions.py - View or edit character convictions."""

import inconnu

__HELP_URL = "https://www.inconnu.app/"


async def convictions_set(ctx, character):
    """Edit character Convictions."""
    try:
        tip = "`/character convictions set` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)

        modal = inconnu.views.ConvictionsModal(character)
        await ctx.send_modal(modal)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


async def convictions_show(ctx, character, player, ephemeral):
    """Show a character's Convictions."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/character convictions show` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        char_convictions = character.convictions
        char_convictions = "\n".join(char_convictions) if char_convictions else "*None*"

        await inconnu.respond(ctx)(
            f"**{character.name}'s Convictions**\n\n{char_convictions}",
            ephemeral=ephemeral
        )

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass
