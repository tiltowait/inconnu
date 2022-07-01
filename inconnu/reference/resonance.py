"""reference/resonance.py - Display a random resonance and temperament."""

from typing import Tuple

import discord

import inconnu

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
    None: "No notable emotions",
}

RESONANCES = list(__DISCIPLINES)


async def random_temperament(ctx, res: str):
    """Generate a random temperament for a given resonance."""
    temperament = __get_temperament()
    if temperament == "Negligible":
        res = None
    await __display_embed(ctx, temperament, res, None)


async def resonance(ctx, **kwargs):
    """Generate and display a resonance."""
    temperament = __get_temperament()
    if temperament != "Negligible":
        add_empty = await inconnu.settings.add_empty_resonance(ctx.guild)
        die, res = __get_resonance(add_empty)
    else:
        die = None
        res = None

    await __display_embed(ctx, temperament, res, die, **kwargs)


async def __display_embed(ctx, temperament, res, die, **kwargs):
    """Display the resonance in an embed."""
    if res:
        title = f"{temperament} {res} Resonance"
    else:
        title = f"{temperament} Resonance"

    embed = discord.Embed(title=title)
    embed.set_author(
        name=kwargs.get("character", ctx.user.display_name),
        icon_url=inconnu.get_avatar(ctx.user),
    )
    embed.add_field(name="Disciplines", value=__DISCIPLINES.get(res, "None"))
    embed.add_field(name="Emotions & Conditions", value=__EMOTIONS[res])
    if die:
        embed.set_footer(text=f"Rolled {die} for the Resonance")

    await inconnu.respond(ctx)(embed=embed)


def __get_temperament() -> str:
    """Randomgly generate a temperament."""
    die = inconnu.d10()

    if 1 <= die <= 5:
        return "Negligible"

    if 6 <= die <= 8:
        return "Fleeting"

    # 9-10 requires a re-roll

    if 1 <= inconnu.d10() <= 8:
        return "Intense"

    return "Acute"


def __get_resonance(add_empty: bool) -> Tuple[int, str]:
    """Return a random resonance plus its associated die."""
    cap = 12 if add_empty else 10
    die = inconnu.random(cap)

    if 1 <= die <= 3:
        return (die, "Phlegmatic")

    if 4 <= die <= 6:
        return (die, "Melancholy")

    if 7 <= die <= 8:
        return (die, "Choleric")

    if 9 <= die <= 10:
        return (die, "Sanguine")

    return (die, "Empty")
