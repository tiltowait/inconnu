"""reference/resonance.py - Display a random resonance and temperament."""

import random
from typing import Tuple

import discord

import inconnu.settings

__DISCIPLINES = {
    "Choleric": "Celerity, Potence",
    "Melancholy": "Fortitude, Obfuscate",
    "Phlegmatic": "Auspex, Dominate",
    "Sanguine": "Blood Sorcery, Presence",
    "Animal Blood": "Animalism, Protean",
    "Empty": "Oblivion",
}

__EMOTIONS = {
    "Choleric": "Angry, violent, bullying, passionate, envious",
    "Melancholy": "Sad, scared, intellectual, depressed, grounded",
    "Phlegmatic": "Lazy, apathetic, calm, controlling, sentimental",
    "Sanguine": "Horny, happy, addicted, active, flighty, enthusiastic",
    "Animal Blood": "No emotion",
    "Empty": "No emotion",
}

RESONANCES = list(__DISCIPLINES.keys())


async def random_temperament(ctx, res: str):
    """Generate a random temperament for a given resonance."""
    temperament = __get_temperament()

    if await inconnu.settings.accessible(ctx.user):
        await __display_text(ctx, temperament, res, None)
    else:
        await __display_embed(ctx, temperament, res, None)


async def resonance(ctx):
    """Generate and display a resonance."""
    temperament = __get_temperament()
    die, res = __get_resonance()

    if await inconnu.settings.accessible(ctx.user):
        await __display_text(ctx, temperament, res, die)
    else:
        await __display_embed(ctx, temperament, res, die)


async def __display_text(ctx, temperament, res, die):
    """Display the resonance in text mode."""
    contents = []
    contents.append(f"{temperament} {res} Resonance\n")
    contents.append(f"Disciplines: {__DISCIPLINES[res]}")
    contents.append(f"Emotions & Conditions: {__EMOTIONS[res]}")
    if die:
        contents.append(f"```Rolled {die} on the Resonance roll.```")

    await ctx.respond("\n".join(contents))


async def __display_embed(ctx, temperament, res, die):
    """Display the resonance in an embed."""
    embed = discord.Embed(title=f"{temperament} {res} Resonance")
    embed.set_author(name=ctx.user.display_name, icon_url=inconnu.get_avatar(ctx.user))
    embed.add_field(name="Disciplines", value=__DISCIPLINES[res])
    embed.add_field(name="Emotions & Conditions", value=__EMOTIONS[res])
    if die:
        embed.set_footer(text=f"Rolled {die} for the Resonance")

    await ctx.respond(embed=embed)


def __get_temperament() -> str:
    """Randomgly generate a temperament."""
    die = random.randint(1, 10)

    if 1 <= die <= 5:
        return "Negligible"

    if 6 <= die <= 8:
        return "Fleeting"

    # 9-10 requires a re-roll

    if 1 <= random.randint(1, 10) <= 8:
        return "Intense"

    return "Acute"


def __get_resonance() -> Tuple[int, str]:
    """Return a random resonance plus its associated die."""
    die = random.randint(1, 10)

    if 1 <= die <= 3:
        return (die, "Phlegmatic")

    if 4 <= die <= 6:
        return (die, "Melancholy")

    if 7 <= die <= 8:
        return (die, "Choleric")

    return (die, "Sanguine")
