"""reference/resonance.py - Display a random resonance and temperament."""

import sqlite3
from typing import NamedTuple

import discord

import inconnu
import services
from ctx import AppCtx
from models import ResonanceMode
from utils import get_avatar

STANDARD_DISCIPLINES = {
    "Choleric": "Celerity, Potence",
    "Melancholy": "Fortitude, Obfuscate",
    "Phlegmatic": "Auspex, Dominate",
    "Sanguine": "Blood Sorcery, Presence",
    "Animal Blood": "Animalism, Protean",
    "Empty": "Oblivion",
}

TATTERED_DISCIPLINES = {
    "Choleric": "Animalism, Celerity, Potence",
    "Melancholy": "Fortitude, Obfuscate, Oblivion",
    "Phlegmatic": "Auspex, Dominate",
    "Sanguine": "Blood Sorcery, Presence, Protean",
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
    "": "No notable emotions",
}

# No need to export a "TATTERED_RESONANCES" list: We can't dynamically change
# the options based on guild settings (we can ... but it is slow and bad UX),
# so we'll allow animal and empty even though they're technically wrong, but
# the Big Four will still be correct when called in get_resonance().
STANDARD_RESONANCES = list(STANDARD_DISCIPLINES)


class Dyscrasia(NamedTuple):
    """Represents Dyscrasia data from the database."""

    name: str
    description: str
    page: int


async def random_temperament(ctx: AppCtx, res: str):
    """Generate a random temperament for a given resonance."""
    temperament = _get_temperament()
    if temperament == "Negligible":
        res = ""

    mode = await services.settings.resonance_mode(ctx.guild)
    await _display_embed(ctx, temperament, res, None, mode)


async def resonance(ctx, **kwargs):
    """Generate and display a resonance."""
    temperament = _get_temperament()
    mode = await services.settings.resonance_mode(ctx.guild)

    if temperament != "Negligible":
        die, res = get_resonance(mode)
    else:
        die = None
        res = ""

    await _display_embed(ctx, temperament, res, die, mode, **kwargs)


async def _display_embed(
    ctx: AppCtx,
    temperament: str,
    res: str,
    die: int | None,
    mode: ResonanceMode,
    **kwargs,
):
    """Display the resonance in an embed."""
    if res:
        title = f"{temperament} {res} Resonance"
    else:
        title = f"{temperament} Resonance"

    embed = discord.Embed(title=title)
    embed.set_author(
        name=kwargs.get("character", ctx.user.display_name),
        icon_url=get_avatar(ctx.user),
    )
    if mode == ResonanceMode.TATTERED_FACADE:
        disciplines = TATTERED_DISCIPLINES.get(res, "None")
    else:
        disciplines = STANDARD_DISCIPLINES.get(res, "None")

    embed.add_field(name="Disciplines", value=disciplines)
    embed.add_field(name="Emotions & Conditions", value=__EMOTIONS[res])

    if res and temperament == "Acute":
        if dys := get_dyscrasia(res):
            embed.add_field(
                name=f"Dyscrasia: {dys.name}",
                value=f"{dys.description} `(p. {dys.page})`",
                inline=False,
            )
    if die is not None:
        embed.set_footer(text=f"Rolled {die} for the Resonance")

    await ctx.respond(embed=embed)


def _get_temperament() -> str:
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


def get_resonance(mode: ResonanceMode) -> tuple[int, str]:
    """Return a random resonance plus its associated die."""
    cap = 12 if mode == ResonanceMode.ADD_EMPTY else 10
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


def get_dyscrasia(resonance: str) -> Dyscrasia | None:
    """Get a random dyscrasia for a resonance."""
    conn = sqlite3.connect("src/inconnu/reference/dyscrasias.db")
    conn.row_factory = lambda _, r: Dyscrasia(*r)
    cur = conn.cursor()

    res = cur.execute(
        "SELECT name, description, page FROM dyscrasias WHERE resonance=? ORDER BY RANDOM()",
        (resonance,),
    ).fetchone()

    conn.close()
    return res
