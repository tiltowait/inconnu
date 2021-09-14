"""misc/frenzy.py - Perform a frenzy check."""

import random

import discord

from .. import common
from ..vchar import errors, VChar

async def process(ctx, difficulty: int, character: str):
    """Perform a frenzy check."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = f"`/frenzy` `difficulty:{difficulty}` `character:CHARACTER`"
        character = await common.select_character(ctx, err, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
        return

    dice = [random.randint(1, 10) for _ in range(character.frenzy_resist)]

    if sum(map(lambda die: die >= 6, dice)) >= difficulty:
        if dice.count(10) >= 2:
            title = "Critical Success!"
            message = "Resist frenzy without losing a turn."
            color = 0x00FF00
        else:
            title = "Success!"
            message = "You spend 1 turn resisting frenzy."
            color = 0x7777FF
    else:
        title = "Failure!"
        message = "You succumb to the Beast."
        color = 0x5C0700
        character.log("frenzy")

    embed = discord.Embed(
        title=title,
        description=message,
        colour=color
    )
    author_field = f"{character.name}: Frenzy vs diff. {difficulty}"
    embed.set_author(name=author_field, icon_url=ctx.author.avatar_url)
    embed.set_footer(text="Dice: " + ", ".join(map(str, dice)))

    await ctx.respond(embed=embed)
