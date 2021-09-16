"""traits/show.py - Display character traits."""

import discord

from .. import common
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=displaying-traits"


async def parse(ctx, character: str, player: str):
    """Present a character's traits to its owner."""
    try:
        owner = await common.player_lookup(ctx, player)
        character = VChar.fetch(ctx.guild.id, owner.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = "`/traits list` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL,
            ("Proper syntax", tip),
            player=owner
        )

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.present_error(ctx, err, author=owner, help_url=__HELP_URL)
        return
    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
        return

    traits = map(lambda row: f"**{row[0]}**: {row[1]}", character.traits.items())

    embed = discord.Embed(
        title="Traits",
        description="\n".join(traits)
    )
    embed.set_author(name=character.name, icon_url=owner.avatar_url)
    embed.set_footer(text="To see HP, WP, etc., use /character display")

    await ctx.respond(embed=embed, hidden=True)
