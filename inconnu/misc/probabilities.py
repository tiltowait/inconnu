"""misc/probabilities.py - Calculate the probability of a given roll."""

import os
from collections import defaultdict

import discord
import pymongo

from .. import common
from .. import roll
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=probability-calculation"
__STRATEGIES = {
    "reroll_failures": "Re-rolling Failures",
    "maximize_criticals": "Maximizing Crits",
    "avoid_messy": "Avoiding Messy Crits",
    "risky": "Riskily Avoiding Messy Crits"
}


async def process(ctx, syntax: str, strategy=None, character=None):
    """Calculate the probabilities surrounding a roll."""
    if roll.needs_character(syntax):
        if ctx.guild is None:
            await ctx.respond("Sorry, you can't use traits in DMs.")
            return

        try:
            character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

        except errors.UnspecifiedCharacterError as err:
            tip = f"`/probability` `roll:{syntax}` `character:CHARACTER`"
            character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

            if character is None:
                # They didn't select a character
                return
        except errors.CharacterError as err:
            await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
            return
    else:
        character = None

    try:
        args = syntax.split()
        _, params = roll.prepare_roll(character, *args)
        probabilities = __get_probabilities(params, strategy)

        await __display_probabilities(ctx, params, strategy, probabilities)

    except (SyntaxError, ValueError) as err:
        name = character.name if character is not None else ctx.author.display_name
        await common.display_error(ctx, name, str(err), __HELP_URL)


async def __display_probabilities(ctx, params, strategy: str, probs: dict):
    """Display the probabilities."""
    title = f"Pool {params.pool} | Hunger {params.hunger} | Diff. {params.difficulty}"
    if strategy is not None:
        title += " | " + __STRATEGIES[strategy]

    uncomplicated = probs["success"] + probs["critical"]
    description = f"**{uncomplicated:.1%}** success without complication"
    description += f"\n**{probs['total_successes']:.1f}** average successes"
    description += f"\n**{probs['margin']:.1f}** average margin"

    if strategy is not None:
        description = f"**{__STRATEGIES[strategy]}**\n\n{description}"

    embed = discord.Embed(
        title=f"Pool {params.pool} | Hunger {params.hunger} | Diff. {params.difficulty}",
        description=description,
        colour=0x000000
    )
    embed.set_author(name="Outcome Probabilities")
    embed.set_footer(text="Simulated over 10,000 runs")

    # Breakdown field
    success = roll.dicemoji.emojify_die(6, False) + f"{probs['success']:.1%} Success"
    messy = roll.dicemoji.emojify_die(10, True) + f"{probs['messy']:.1%} Messy Critical"
    total_fail = roll.dicemoji.emojify_die(3, True) + f"{probs['total_fail']:.1%} Total Failure"
    bestial = roll.dicemoji.emojify_die(1, True) + f"{probs['bestial']:.1%} Bestial Failure"

    breakdown = ""
    if params.pool > params.hunger:
        breakdown += roll.dicemoji.emojify_die(10, False) + f" {probs['critical']:.1%} Critical Win"

    breakdown += f"\n{success}\n{messy}\n------\n"

    if probs["fail"] != 0:
        # Only show regular failure if there's a distinction between it and total failure
        breakdown += roll.dicemoji.emojify_die(3, False) + f"{probs['fail']:.1%} Failure\n"

    breakdown += f"{total_fail}\n{bestial}"

    embed.add_field(name="Breakdown", value=breakdown)

    await ctx.respond(embed=embed)


def __get_probabilities(params, strategy):
    """Retrieve the probabilities from storage or, if not calculated yet, generate them."""
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    col = client.inconnu.probabilities

    probs = col.find_one({
        "pool": params.pool,
        "hunger": params.hunger,
        "difficulty": params.difficulty,
        "strategy": strategy
    })

    if probs is None:
        probs = __simulate(params, strategy)

        # Save the probabilities
        col.insert_one({
            "pool": params.pool,
            "hunger": params.hunger,
            "difficulty": params.difficulty,
            "strategy": strategy,
            "probabilities": probs
        })
    else:
        probabilities = probs["probabilities"]
        probs = defaultdict(lambda: 0)
        probs.update(probabilities)

    client.close()
    return probs


def __simulate(params, strategy):
    """Simulate 1000 rolls and calculate the probabilities of each potential outcome."""
    trials = 10000
    totals = defaultdict(lambda: 0)
    outcomes = defaultdict(lambda: 0)

    for _ in range(trials):
        outcome = roll.roll_pool(params)

        # Check reroll options
        if strategy is not None:
            if strategy == "reroll_failures" and outcome.can_reroll_failures:
                outcome = roll.reroll(strategy, outcome)
            elif strategy == "maximize_criticals" and outcome.can_maximize_criticals:
                outcome = roll.reroll(strategy, outcome)
            elif strategy == "avoid_messy" and outcome.can_avoid_messy_critical:
                outcome = roll.reroll(strategy, outcome)
            elif strategy == "risky" and outcome.can_risky_messy_critical:
                outcome = roll.reroll(strategy, outcome)

        totals["total_successes"] += outcome.total_successes
        totals["margin"] += outcome.margin
        outcomes[outcome.outcome] += 1

    probabilities = defaultdict(lambda: 0)
    probabilities["total_successes"] = totals["total_successes"] / trials
    probabilities["margin"] = totals["margin"] / trials

    for outcome, frequency in outcomes.items():
        probabilities[outcome] = frequency / trials

    return probabilities
