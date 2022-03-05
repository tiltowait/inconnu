"""misc/cripple.py - Roll against the crippling injury chart."""

import random
from types import SimpleNamespace

import discord

import inconnu.common

__HELP_URL = "https://www.inconnu-bot.com"

async def cripple(ctx, damage: int):
    """Roll against the crippling injury chart."""
    try:
        if damage is None:
            tip = "/cripple `damage:DAMAGE` `character:CHARACTER`"
            character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)
            damage = character.aggravated_hp
        else:
            character = None # Do not allow explicit damage on a character

        if damage < 1:
            await ctx.respond(
                "You need some Aggravated damage to sustain a crippling injury!",
                ephemeral=True
            )
            return

        injuries = __get_injury(damage)
        await __display_injury(ctx, damage, injuries)

    except inconnu.common.FetchError:
        pass


async def __display_injury(ctx, damage, injuries):
    """Display a crippling injury."""
    # We don't use the modular display, because we don't necessarily have a character here

    embed = discord.Embed(
        title="Crippling Injury",
        description=f"`{damage}` Aggravated damage sustained this turn."
    )
    embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar)

    for injury in injuries:
        embed.add_field(name=injury.injury, value=injury.effect, inline=False)

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
