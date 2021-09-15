"""misc/rousemorse.py - Perform rouse checks."""

import random

import discord

from .. import common
from ..character.display import trackmoji
from ..vchar import errors, VChar

__HELP = {
    "remorse": "https://www.inconnu-bot.com/#/additional-commands?id=remorse-checks",
    "rouse": "https://www.inconnu-bot.com/#/additional-commands?id=rouse-checks"
}


async def parse(ctx, key: str, character: str, count=0, purpose=None):
    """Determine whether to perform a rouse or remorse check."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = f"`/{key}` `character:CHARACTER`"
        url = __HELP[key]
        character = await common.select_character(ctx, err, url, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, url)
        return

    if key == "rouse":
        await __rouse_result(ctx, character, count, purpose)
    elif key == "remorse":
        await __remorse_result(ctx, character)


async def __rouse_result(ctx, character: VChar, rolls: int, purpose: str):
    """Process the rouse result and display to the user."""
    dice = [random.randint(1, 10) for _ in range(rolls)]
    ones, successes, tens = __count_successes(dice)
    total_rouses = len(dice)

    hunger_gain = total_rouses - successes

    new_hunger = character.hunger + hunger_gain
    frenzy = new_hunger > 5
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
    embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)

    field_name = "New Hunger" if "ailure" in title else "Hunger"
    embed.add_field(name=field_name, value=trackmoji.emojify_hunger(new_hunger))

    if frenzy:
        embed.add_field(
            name="Roll against Hunger Frenzy",
            value="You failed a Rouse check at Hunger 5 and should run the `/frenzy` command.",
            inline=False
        )

    footer = purpose + "\n" if purpose is not None else ""
    potential_stains = tens + ones
    if potential_stains > 0:
        stains_txt = common.pluralize(potential_stains, "stain")
        footer += f"If this was an Oblivion roll, gain {stains_txt}!"

    embed.set_footer(text=footer)

    await ctx.respond(embed=embed)
    character.hunger = new_hunger
    character.log("rouse", rolls)


async def __remorse_result(ctx, character: VChar):
    """Process the remorse result and display to the user."""
    if character.stains == 0:
        await ctx.respond(f"{character.name} has no stains! No remorse necessary.", hidden=True)
        return

    successful = __remorse_roll(character)

    embed = discord.Embed(
        title="Remorse Success" if successful else "Remorse Fail"
    )
    embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)
    embed.add_field(name="Humanity", value=trackmoji.emojify_humanity(character.humanity, 0))

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


def __remorse_roll(character: VChar) -> bool:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = unfilled if unfilled > 0 else 1
    successful = False

    for _ in range(rolls):
        throw = random.randint(1, 10)
        if throw >= 6:
            successful = True
            break

    if not successful:
        character.humanity -= 1
        character.log("degen")
    else:
        character.stains = 0

    character.log("remorse")

    return successful
