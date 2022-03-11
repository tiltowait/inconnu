"""character/convictions.py - View or edit character convictions."""

import inconnu

__HELP_URL = "https://www.inconnu-bot.com/"


async def convictions(ctx, character, player, ephemeral):
    """View or edit character convictions."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/character convictions` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        if (owner.id != ctx.user.id) or ephemeral:
            # Admin lookup. Don't show the modal.
            char_convictions = character.convictions
            char_convictions = "\n".join(char_convictions) if char_convictions else "*None*"

            await inconnu.respond(ctx)(
                f"**{character.name}'s Convictions**\n\n{char_convictions}",
                ephemeral=ephemeral
            )
        else:
            modal = inconnu.views.ConvictionsModal(character)
            await ctx.send_modal(modal)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass
