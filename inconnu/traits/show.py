"""traits/show.py - Display character traits."""

import discord

from .. import common

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=displaying-traits"


async def show(ctx, character: str, player: discord.Member):
    """Present a character's traits to its owner."""
    try:
        owner = await common.player_lookup(ctx, player)
        tip = "`/traits list` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)


        traits = map(lambda row: f"**{row[0]}**: {row[1]}", character.traits.items())

        embed = discord.Embed(
            title="Traits",
            description="\n".join(traits)
        )
        embed.set_author(name=character.name, icon_url=owner.display_avatar)
        embed.set_footer(text="To see HP, WP, etc., use /character display")

        await ctx.respond(embed=embed, hidden=True)

    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except common.FetchError:
        pass
