"""traits/show.py - Display character traits."""

import discord

from .. import common
from ..constants import character_db

async def parse(ctx, *args):
    """Present a character's traits to its owner."""
    char_name, char_id = await common.get_character(ctx.guild.id, ctx.author.id, *args)

    if char_name is None:
        message = await common.character_options_message(ctx.guild.id, ctx.author.id, "")
        await ctx.reply(message)
        return

    # Character obtained
    traits = await character_db.get_all_traits(char_id)
    traits = list(map(lambda row: f"**{row[0]}**: {row[1]}", list(traits.items())))

    embed = discord.Embed(
        title="Traits",
        description="\n".join(traits)
    )
    embed.set_author(name=f"{char_name} on {ctx.guild.name}", icon_url=ctx.guild.icon_url)
    embed.set_footer(text=f"To see HP, WP, etc., use //display on {ctx.guild.name}")

    await ctx.reply("Check your DMs!")
    await ctx.author.send(embed=embed)
