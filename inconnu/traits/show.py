"""traits/show.py - Display character traits."""

import discord

from .. import common
from ..constants import character_db

async def parse(ctx, character=None):
    """Present a character's traits to its owner."""
    try:
        char_name, char_id = await common.match_character(ctx.guild.id, ctx.author.id, character)

        # Character obtained
        traits = await character_db.get_all_traits(char_id)
        traits = list(map(lambda row: f"**{row[0]}**: {row[1]}", list(traits.items())))

        embed = discord.Embed(
            title="Traits",
            description="\n".join(traits)
        )
        embed.set_author(name=f"{char_name} on {ctx.guild.name}", icon_url=ctx.guild.icon_url)
        embed.set_footer(text=f"To see HP, WP, etc., use /character display")

        await ctx.respond(embed=embed, hidden=True)

    except ValueError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return
