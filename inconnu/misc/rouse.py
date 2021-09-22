"""misc/rouse.py - Perform rouse checks."""

import random
from types import SimpleNamespace

from .. import common
from .. import character as char
from ..vchar import VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=rouse-checks"


async def rouse(ctx, count: int, character: str, purpose: str, reroll: bool):
    """
    Perform a remorse check on a given character and display the results.
    Args:
        count (int): The number of rouse checks to make
        character (str): (Optional): The name of a character
        purpose (str): The reason for the rouse
        reroll (bool): Whether failures should be re-rolled
    """
    try:
        tip = "`/rouse` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        outcome = __rouse_roll(character, count, reroll)
        await __display_outcome(ctx, character, outcome, purpose)

    except common.FetchError:
        pass


async def __display_outcome(ctx, character: VChar, outcome, purpose):
    """Process the rouse result and display to the user."""
    if outcome.total == 1:
        title = "Rouse Success" if outcome.successes == 1 else "Rouse Failure"
    else:
        successes = common.pluralize(outcome.successes, "success")
        failures = common.pluralize(outcome.failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    if outcome.frenzy:
        custom = [(
            "Roll against Hunger Frenzy",
            "You failed a Rouse check at Hunger 5 and should run the `/frenzy` command."
        )]
    else:
        custom = None

    footer = []
    if purpose is not None:
        footer.append(purpose)
    if outcome.reroll:
        footer.append("Re-rolling failures")
    if outcome.stains > 0:
        stains_txt = common.pluralize(outcome.stains, "stain")
        footer.append(f"If this was an Oblivion roll, gain {stains_txt}!")
    footer = "\n".join(footer)


    hunger_title = "New Hunger" if "ailure" in title else "Hunger"

    await char.display(ctx, character,
        title=title,
        footer=footer,
        fields=[(hunger_title, char.HUNGER)],
        custom=custom
    )


def __rouse_roll(character: VChar, rolls: int, reroll: bool):
    """Perform a Rouse roll."""
    successes = 0
    failures = 0
    stains = 0

    for _ in range(rolls):
        die = random.randint(1, 10)
        if reroll and die < 6:
            die = random.randint(1, 10)

        if die in [1, 10]:
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
