"""traits/show.py - Display character traits."""

import discord

from .. import common
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=displaying-traits"


async def parse(ctx, character=None):
    """Present a character's traits to its owner."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = "`/traits list` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return

    traits = map(lambda row: f"**{row[0]}**: {row[1]}", character.traits.items())

    embed = discord.Embed(
        title="Traits",
        description="\n".join(traits)
    )
    embed.set_author(name=character.name, icon_url=ctx.guild.icon_url)
    embed.set_footer(text="To see HP, WP, etc., use /character display")

    await ctx.respond(embed=embed, hidden=True)
