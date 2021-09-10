"""resonance.py - Display a random resonance and temperament."""

import random

import discord

__DISCIPLINES = {
    "Choleric": "Celerity, Potence",
    "Melancholy": "Fortitude, Obfuscate",
    "Phlegmatic": "Auspex, Dominate",
    "Sanguine": "Blood Sorcery, Presence",
    "Animal Blood": "Animalism, Protean",
    "Empty": "Oblivion"
}

__EMOTIONS = {
    "Choleric": "Angry, violent, bullying, passionate, envious",
    "Melancholy": "Sad, scared, intellectual, depressed, grounded",
    "Phlegmatic": "Lazy, apathetic, calm, controlling, sentimental",
    "Sanguine": "Horny, happy, addicted, active, flighty, enthusiastic",
}


async def generate(ctx):
    """Generate and display a resonance."""
    temperament = __get_temperament()
    die, resonance = __get_resonance()

    embed = discord.Embed(
        title=f"{temperament} {resonance} Resonance"
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    embed.add_field(name="Disciplines", value=__DISCIPLINES[resonance])
    embed.add_field(name="Emotions & Conditions", value=__EMOTIONS[resonance])
    embed.set_footer(text=f"Rolled {die} on the Resonance roll")

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


def __get_resonance() -> tuple:
    """Return a random resonance plus its associated die."""
    die = random.randint(1, 10)

    if 1 <= die <= 3:
        return (die, "Phlegmatic")

    if 4 <= die <= 6:
        return (die, "Melancholy")

    if 7 <= die <= 8:
        return (die, "Choleric")

    return (die, "Sanguine")
