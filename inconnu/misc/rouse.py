"""misc/rouse.py - Perform rouse checks."""

import random
from types import SimpleNamespace

import discord

from .. import common
from ..character.display import trackmoji
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=rouse-checks"


async def process(ctx, count: int, character: str, purpose: str, reroll: bool):
    """
    Perform a remorse check on a given character and display the results.
    Args:
        count (int): The number of rouse checks to make
        character (str): (Optional): The name of a character
        purpose (str): The reason for the rouse
        reroll (bool): Whether failures should be re-rolled
    """
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = "`/rouse` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
        return

    outcome = __rouse_roll(character, count, reroll)
    await __display_outcome(ctx, character, outcome, purpose)


async def __display_outcome(ctx, character: VChar, outcome, purpose):
    """Process the rouse result and display to the user."""
    if outcome.total == 1:
        title = "Rouse Success" if outcome.successes == 1 else "Rouse Failure"
    else:
        successes = common.pluralize(outcome.successes, "success")
        failures = common.pluralize(outcome.failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    embed = discord.Embed(
        title=title
    )
    embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)

    field_name = "New Hunger" if "ailure" in title else "Hunger"
    embed.add_field(name=field_name, value=trackmoji.emojify_hunger(character.hunger))

    if outcome.frenzy:
        embed.add_field(
            name="Roll against Hunger Frenzy",
            value="You failed a Rouse check at Hunger 5 and should run the `/frenzy` command.",
            inline=False
        )

    footer = []
    if purpose is not None:
        footer.append(purpose)
    if outcome.reroll:
        footer.append("Re-rolling failures")
    if outcome.stains > 0:
        stains_txt = common.pluralize(outcome.stains, "stain")
        footer.append(f"If this was an Oblivion roll, gain {stains_txt}!")
    footer = "\n".join(footer)

    embed.set_footer(text=footer)

    await ctx.respond(embed=embed)


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
