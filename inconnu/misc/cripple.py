"""misc/cripple.py - Roll against the crippling injury chart."""

import random
from types import SimpleNamespace

import discord

from .. import common
from ..character.display import trackmoji

__HELP_URL = "https://www.inconnu-bot.com"

async def cripple(ctx, damage: int, character: str):
    """Roll against the crippling injury chart."""
    if ctx.guild is None and character is not None:
        await ctx.respond("You can't look up characters in DMs!")
        return

    try:
        if damage is None:
            tip = "/cripple `damage:DAMAGE` `character:CHARACTER`"
            character = await common.fetch_character(ctx, character, tip, __HELP_URL)
            damage = character.agg_health
        else:
            character = None # Do not allow explicit damage on a character

        if damage < 1:
            await ctx.respond(
                "You need some Aggravated damage to sustain a crippling injury!",
                ephemeral=True
            )
            return

        injuries = __get_injury(damage)
        await __display_injury(ctx, damage, character, injuries)

        if character is not None:
            # Log the injuries
            injuries = " / ".join([injury.injury for injury in injuries])
            character.log_injury(injuries)

    except common.FetchError:
        pass


async def __display_injury(ctx, damage, character, injuries):
    """Display a crippling injury."""
    # We don't use the modular display, because we don't necessarily have a character here

    embed = discord.Embed(title="Crippling Injury")

    author = character.name if character is not None else ctx.user.display_name
    embed.set_author(name=f"{author} | {damage} Agg", icon_url=ctx.user.display_avatar)

    for injury in injuries:
        embed.add_field(name=injury.injury, value=injury.effect, inline=False)

    if character is not None:
        embed.add_field(name="Health", value=trackmoji.emojify_track(character.health))

    if len(injuries) > 1:
        embed.set_footer(text="The Storyteller chooses which injury applies.")

    await ctx.respond(embed=embed)


def __get_injury(damage: int):
    """Get a random injury from the chart."""
    roll = damage + random.randint(1, 10)

    injury = []
    effect = []

    if 1 <= roll <= 6:
        injury.append("Stunned")
        effect.append("Spend 1 Willpower or lose one turn.")

    elif 7 <= roll <= 8:
        injury.append("Severe head trauma")
        effect.append("Physical rolls lose 1 die; Mental rolls lose 2.")

    elif 9 <= roll <= 10:
        injury.append("Broken limb or joint")
        effect.append("Rolls using the affected limb lose 3 dice.")
        injury.append("Blinded")
        effect.append("Vision-related rolls lose 3 dice.")

    elif roll == 11:
        injury.append("Massive wound")
        effect.append("All rolls lose 2 dice. Add 1 to all damage suffered.")

    elif roll == 12:
        injury.append("Crippled")
        effect.append("Limb is lost or mangled beyond use. Lose 3 dice when using it.")

    elif roll >= 13:
        injury.append("Death or torpor")
        effect.append("Mortals die. Vampires enter immediate torpor.")

    injuries = []
    for injury, effect in zip(injury, effect):
        injuries.append(SimpleNamespace(injury=injury, effect=effect))

    return  injuries
