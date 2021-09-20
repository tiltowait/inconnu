"""misc/remorse.py - Perform a remorse check."""

import random

import discord

from .. import common
from ..character.display import trackmoji
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=remorse-checks"


async def remorse(ctx, character=None):
    """Perform a remorse check on a given character."""
    try:
        tip = "`/remorse` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        # Character obtained
        if character.stains == 0:
            await ctx.respond(f"{character.name} has no stains! No remorse necessary.", hidden=True)
            return

        remorseful = __remorse_roll(character)
        await __display_outcome(ctx, character, remorseful)

    except common.FetchError:
        pass


async def __display_outcome(ctx, character: VChar, remorseful: bool):
    """Process the remorse result and display to the user."""
    embed = discord.Embed(
        title="Remorse Success" if remorseful else "Remorse Fail"
    )
    embed.set_author(name=character.name, icon_url=ctx.author.display_avatar)
    embed.add_field(name="Humanity", value=trackmoji.emojify_humanity(character.humanity, 0))

    if remorseful:
        embed.set_footer(text="You keep the Beast at bay. For now.")
    else:
        embed.set_footer(text="The downward spiral continues ...")

    await ctx.respond(embed=embed)


def __remorse_roll(character: VChar) -> bool:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = unfilled if unfilled > 0 else 1
    successful = False

    for _ in range(rolls):
        throw = random.randint(1, 10)
        if throw >= 6:
            successful = True
            break

    if not successful:
        character.humanity -= 1
        character.log("degen")
    else:
        character.stains = 0

    character.log("remorse")

    return successful
