"""rousemorse.py - Perform rouse checks."""

import random

import discord

from . import common
from .display import Trackmoji
from .constants import character_db

__TRACKMOJI = None

async def parse(ctx, key: str, character: str, count=0):
    """Perform a rouse check."""
    global __TRACKMOJI
    if __TRACKMOJI is None:
        __TRACKMOJI = Trackmoji(ctx.bot)

    char_name, char_id = await common.get_character(ctx.guild.id, ctx.author.id, character)

    if char_name is None:
        if character is not None:
            message = await common.character_options_message(ctx.guild.id, ctx.author.id, character)
        else:
            message = "You have no characters!"
        await ctx.respond(message, hidden=True)
        return

    if key == "rouse":
        await __rouse_result(ctx, char_id, char_name, count)
    elif key == "remorse":
        await __remorse_result(ctx, char_id, char_name)


async def __rouse_result(ctx, char_id: int, char_name: int, rolls: int):
    """Process the rouse result and display to the user."""
    current_hunger = await character_db.get_hunger(char_id)
    if current_hunger == 5:
        await ctx.respond(f"{char_name}'s Hunger is already 5!")
        return

    dice = [random.randint(1, 10) for _ in range(rolls)]
    ones, successes, tens = __count_successes(dice)
    total_rouses = len(dice)

    hunger_gain = total_rouses - successes

    new_hunger = current_hunger + hunger_gain
    if new_hunger > 5:
        new_hunger = 5

    # Prepare the embed

    title = None
    if total_rouses == 1:
        title = "Rouse Success" if successes == 1 else "Rouse Failure"
    else:
        failures = total_rouses - successes
        successes = common.pluralize(successes, "success")
        failures = common.pluralize(failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    embed = discord.Embed(
        title=title
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
    embed.add_field(name="New Hunger", value=__TRACKMOJI.emojify_hunger(new_hunger))

    potential_stains = tens + ones
    if potential_stains > 0:
        embed.set_footer(text=f"If this was an Oblivion roll, gain {potential_stains} stains!")

    await ctx.respond(embed=embed)

    # Update the database
    await character_db.set_hunger(char_id, new_hunger)


async def __remorse_result(ctx, char_id: int, char_name: int):
    """Process the remorse result and display to the user."""
    if await character_db.get_stains(char_id) == 0:
        await ctx.respond(f"{char_name} has no stains! No remorse necessary.", hidden=True)
        return

    successful = await __remorse_roll(char_id)
    humanity = await character_db.get_humanity(char_id)

    embed = discord.Embed(
        title="Remorse Success" if successful else "Remorse Fail"
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
    embed.add_field(name="Humanity", value=__TRACKMOJI.emojify_humanity(humanity, 0))

    if successful:
        embed.set_footer(text="You keep the Beast at bay. For now.")
    else:
        embed.set_footer(text="The downward spiral continues ...")

    await ctx.respond(embed=embed)


def __instructions(key: str) -> str:
    """Generate the appropriate usage instructions."""
    message = f"USAGE:\n\n//{key} [CHARACTER]"
    if key == "rouse":
        message += " [ROUSE NUMBER]"
    return message


def __count_successes(dice: list) -> tuple:
    """Count the number of successes and tens in a batch of dice."""
    successes = 0
    tens = 0
    ones = 0

    for die in dice:
        if die >= 6:
            successes += 1
            if die == 10:
                tens += 1
        elif die == 1:
            ones += 1

    return (ones, successes, tens)


async def __remorse_roll(charid: int) -> bool:
    """Perform a remorse roll."""
    humanity = await character_db.get_humanity(charid)
    stains = await character_db.get_stains(charid)

    unfilled = 10 - humanity - stains
    rolls = unfilled if unfilled > 0 else 1
    successful = False

    for _ in range(rolls):
        throw = random.randint(1, 10)
        if throw >= 6:
            successful = True
            break

    if not successful:
        humanity -= 1

    await character_db.set_humanity(charid, humanity)
    return successful
