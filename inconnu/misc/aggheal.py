"""misc/aggheal.py - Heal aggravated damage."""

import random
from types import SimpleNamespace

import discord

from .. import common
from ..character.display import trackmoji
from ..constants import DAMAGE
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/"


async def aggheal(ctx, character: str):
    """Heal a point of aggravated damage."""
    try:
        tip = "`/aggheal` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if character.health.count(DAMAGE.aggravated) == 0:
            await ctx.respond(f"{character.name} has no aggravated damage to heal!", hidden=True)
            return

        outcome = __heal(character)
        await __display_outcome(ctx, character, outcome)

    except common.FetchError:
        pass


def __heal(character: VChar):
    """
    Heal agg damage.
    Does not check if the character has agg damage!
    """
    hunger_gain = 0
    for _ in range(3):
        if random.randint(1, 10) < 6:
            hunger_gain += 1

    frenzy = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        frenzy = True


    # Update the character
    character.hunger += hunger_gain
    character.health = DAMAGE.none + character.health[:-1]

    return SimpleNamespace(gain=hunger_gain, frenzy=frenzy)


async def __display_outcome(ctx, character, outcome):
    """Display the outcome of the healing."""
    gain = "Max Hunger" if character.hunger == 5 else f"Gain {outcome.gain} Hunger"
    embed = discord.Embed(
        title=f"Damage healed | {gain}",
    )
    embed.set_author(name=character.name, icon_url=ctx.author.display_avatar)

    embed.add_field(name="Health", value=trackmoji.emojify_track(character.health), inline=False)
    embed.add_field(name="Hunger", value=trackmoji.emojify_hunger(character.hunger), inline=False)

    if outcome.frenzy:
        embed.set_footer(text="ROLL FOR HUNGER FRENZY!")

    await ctx.respond(embed=embed)
