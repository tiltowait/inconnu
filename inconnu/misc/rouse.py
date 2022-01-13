"""misc/rouse.py - Perform rouse checks."""
# pylint: disable=too-many-arguments

import asyncio
import random
from types import SimpleNamespace

from discord_ui.components import Button

from .frenzy import frenzy
from .. import common
from .. import character as char
from ..settings import Settings
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=rouse-checks"


async def rouse(
    ctx, count: int, character: str, purpose: str, reroll: bool, oblivion="show", message=None
):
    """
    Perform a remorse check on a given character and display the results.
    Args:
        count (int): The number of rouse checks to make
        character (str): (Optional): The name of a character
        purpose (str): The reason for the rouse
        reroll (bool): Whether failures should be re-rolled
        oblivion (bool, default False): Whether to show the Oblivion message.
    """
    try:
        tip = "`/rouse` `character:CHARACTER`"
        if not isinstance(character, VChar):
            character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        if character.splat == "mortal":
            await ctx.respond("Mortals can't make rouse checks.", hidden=True)
        elif character.splat == "ghoul":
            await __damage_ghoul(ctx, character)
        else:
            # Vampire
            outcome = __rouse_roll(character, count, reroll)
            await __display_outcome(ctx, character, outcome, purpose, oblivion, message)

    except common.FetchError:
        pass


async def __display_outcome(ctx, character: VChar, outcome, purpose, oblivion, message):
    """Process the rouse result and display to the user."""
    if outcome.total == 1:
        title = "Rouse Success" if outcome.successes == 1 else "Rouse Failure"
    else:
        successes = common.pluralize(outcome.successes, "success")
        failures = common.pluralize(outcome.failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    if "ailure" in title:
        color = 0xc70f0f
        thumbnail = "https://www.inconnu-bot.com/images/assets/hunger-filled.webp"
    else:
        color = None
        thumbnail = "https://www.inconnu-bot.com/images/assets/hunger-unfilled.webp"

    if outcome.frenzy:
        components = [Button("Hunger Frenzy (DC 4)", color="red")]
        custom = [("Hunger 5 Rouse Failure", "If awakening: Torpor. Otherwise: Roll for frenzy!")]
    else:
        components = None
        custom = None

    footer = []
    fields = [("New Hunger" if "ailure" in title else "Hunger", char.HUNGER)]

    if purpose is not None:
        footer.append(purpose)
    if outcome.reroll:
        footer.append("Re-rolling failures")
    if outcome.stains > 0:
        stains_txt = common.pluralize(outcome.stains, "stain")

        if oblivion == "show":
            footer.append(f"If this was an Oblivion roll, gain {stains_txt}!")
        elif oblivion == "apply":
            character.stains += outcome.stains
            character.log("stains", outcome.stains)
            fields.append((f"Gain {stains_txt}", char.HUMANITY))

    footer = "\n".join(footer)

    msg = await char.display(ctx, character,
        title=title,
        footer=footer,
        message=message,
        fields=fields,
        custom=custom,
        color=color,
        thumbnail=thumbnail,
        components=components
    )

    if outcome.frenzy:
        try:
            btn = await msg.wait_for("button", ctx.bot, timeout=60)
            while btn.author.id != ctx.author.id:
                await btn.respond("This button doesn't belong to you!", hidden=True)
                btn = await msg.wait_for("button", ctx.bot, timeout=60)

            await frenzy(btn, 0, None, character)

        except asyncio.exceptions.TimeoutError:
            pass
        finally:
            await msg.disable_components()


async def __damage_ghoul(ctx, ghoul):
    """Apply Aggravated damage to a ghoul and display."""
    ghoul.aggravated_hp += 1
    await char.display(ctx, ghoul,
        title="Ghoul Rouse Damage",
        message="Ghouls take Aggravated damage instead of making a Rouse check.",
        fields=[("Health", char.HEALTH)],
        footer="V5 Core, p.234"
    )


def __rouse_roll(character: VChar, rolls: int, reroll: bool):
    """Perform a Rouse roll."""
    successes = 0
    failures = 0
    stains = 0

    oblivion = Settings.oblivion_stains(character.guild)

    for _ in range(rolls):
        die = random.randint(1, 10)
        if reroll and die < 6:
            die = random.randint(1, 10)

        if die in oblivion:
            stains += 1

        if die >= 6:
            successes += 1
        else:
            failures += 1

    starting_hunger = character.hunger
    frenzy = starting_hunger + failures > 5
    character.hunger += failures
    gain = starting_hunger - character.hunger

    character.log("rouse", rolls)

    return SimpleNamespace(
        total=rolls,
        successes=successes,
        failures=failures,
        stains=stains,
        frenzy=frenzy,
        gain=gain,
        reroll=reroll
    )
