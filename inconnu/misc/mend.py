"""misc/mend.py - Mend Superficial damage."""

import random
from types import SimpleNamespace

import discord

from .. import common
from ..constants import DAMAGE
from ..character.display import trackmoji

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=mending-damage"


async def mend(ctx, character=None):
    """Mend damage on a character OR the user's only character."""
    try:
        tip = "`/mend` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        outcome = __heal(character)

        if isinstance(outcome, str):
            await ctx.respond(outcome, hidden=True)
        else:
            await __display_outcome(ctx, character, outcome)

    except common.FetchError:
        pass

async def __display_outcome(ctx, character, outcome):
    """Display the results of the mend."""
    embed = discord.Embed(
        title=f"Mended {outcome.mended} damage | Rouse {'Success' if outcome.rouse else 'Failure'}"
    )
    embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)

    embed.add_field(name="Health", value=trackmoji.emojify_track(character.health), inline=False)
    embed.add_field(name="Hunger", value=trackmoji.emojify_hunger(character.hunger), inline=False)

    if outcome.frenzy:
        embed.set_footer(text="ROLL FOR HUNGER FRENZY!")

    await ctx.respond(embed=embed)


def __heal(character):
    """Heal the character and perform the Rouse check."""
    superficial = character.health.count(DAMAGE.superficial)
    if superficial == 0:
        return f"**{character.name}** has no Superficial damage to mend!"

    mending = min(character.mend_amount, superficial)
    superficial -= mending
    aggravated = character.health.count(DAMAGE.aggravated)
    unhurt = len(character.health) - superficial - aggravated

    track = DAMAGE.none * unhurt + DAMAGE.superficial * superficial + DAMAGE.aggravated * aggravated
    character.health = track

    rouse = random.randint(1, 10) >= 6
    if not rouse:
        frenzy = character.hunger == 5
        character.hunger += 1
    else:
        frenzy = False

    return SimpleNamespace(mended=mending, rouse=rouse, frenzy=frenzy)
