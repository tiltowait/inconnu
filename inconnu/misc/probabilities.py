"""misc/probabilities.py - Calculate the probability of a given roll."""

import os
from collections import defaultdict

import discord
import pymongo

from .. import common
from ..roll import Roll
from .. import vr as roll
from ..settings import Settings

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=probability-calculation"
__STRATEGIES = {
    "reroll_failures": "Re-rolling Failures",
    "maximize_criticals": "Maximizing Crits",
    "avoid_messy": "Avoiding Messy Crits",
    "risky": "Riskily Avoiding Messy Crits"
}


async def probability(ctx, syntax: str, strategy=None, character=None):
    """Calculate the probabilities surrounding a roll."""
    if roll.needs_character(syntax):
        if ctx.guild is None:
            await ctx.respond("Sorry, you can't use traits in DMs.")
            return

        try:
            tip = f"`/probability` `roll:{syntax}` `character:CHARACTER`"
            character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        except common.FetchError:
            return

    else:
        character = None

    try:
        args = syntax.split()
        _, params = roll.prepare_roll(character, args)
        probabilities = __get_probabilities(params, strategy)

        if Settings.accessible(ctx.author):
            await __display_text(ctx, params, strategy, probabilities)
        else:
            await __display_embed(ctx, params, strategy, probabilities)

    except (SyntaxError, ValueError) as err:
        await common.present_error(ctx, err, character=character, help_url=__HELP_URL)


async def __display_text(ctx, params, strategy: str, probs: dict):
    """Display the probabilities in plain text."""
    title = "**Outcome Probabilities**\n"
    title += f"*Pool {params.pool} | Hunger {params.hunger} | Diff. {params.difficulty}*"
    if strategy is not None:
        title += " | " + __STRATEGIES[strategy]

    uncomplicated = probs["success"] + probs["critical"]
    description = f"**{uncomplicated:.2%}** success without complication"
    description += f"\n**{probs['total_successes']:.2f}** average successes"
    description += f"\n**{probs['margin']:.2f}** average margin"

    if strategy is not None:
        description = f"**{__STRATEGIES[strategy]}**\n\n{description}"

    # Breakdown field

    # We show the following fields in this order:
    # Critical (Opt)
    # Success - Technically optional, but we will always show it
    # Messy (Opt)
    # ---
    # Failure (Opt)
    # Total Faiiure
    # Bestial (Opt)

    breakdown = ["**Breakdown**"]
    if probs["critical"] != 0:
        breakdown.append(f"{probs['critical']:.2%} Critical Win")

    breakdown.append(f"{probs['success']:.2%} Success")

    if probs["messy"] != 0:
        breakdown.append(f"{probs['messy']:.2%} Messy Critical")

    breakdown.append("------")

    if probs["fail"] != 0:
        # Only show regular failure if there's a distinction between it and total failure
        breakdown.append(f"{probs['fail']:.2%} Failure")

    breakdown.append(f"{probs['total_fail']:.2%} Total Failure")

    if probs["bestial"] != 0:
        breakdown.append(f"{probs['bestial']:.2%} Bestial Failure")

    message = title + "\n" + "\n".join(breakdown)
    await ctx.respond(message)


async def __display_embed(ctx, params, strategy: str, probs: dict):
    """Display the probabilities in a nice embed."""
    title = f"Pool {params.pool} | Hunger {params.hunger} | Diff. {params.difficulty}"
    if strategy is not None:
        title += " | " + __STRATEGIES[strategy]

    uncomplicated = probs["success"] + probs["critical"]
    description = f"**{uncomplicated:.2%}** success without complication"
    description += f"\n**{probs['total_successes']:.2f}** average successes"
    description += f"\n**{probs['margin']:.2f}** average margin"

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

    # We show the following fields in this order:
    # Critical (Opt)
    # Success - Technically optional, but we will always show it
    # Messy (Opt)
    # ---
    # Failure (Opt)
    # Total Faiiure
    # Bestial (Opt)

    breakdown = []
    if probs["critical"] != 0:
        crit = roll.dicemoji.emojify_die(10, False) + f"{probs['critical']:.2%} Critical Win"
        breakdown.append(crit)

    success = roll.dicemoji.emojify_die(6, False) + f"{probs['success']:.2%} Success"
    breakdown.append(success)

    if probs["messy"] != 0:
        messy = roll.dicemoji.emojify_die(10, True) + f"{probs['messy']:.2%} Messy Critical"
        breakdown.append(messy)

    breakdown.append("------")

    if probs["fail"] != 0:
        # Only show regular failure if there's a distinction between it and total failure
        fail = roll.dicemoji.emojify_die(3, False) + f"{probs['fail']:.2%} Failure"
        breakdown.append(fail)

    total = roll.dicemoji.emojify_die(3, True) + f"{probs['total_fail']:.2%} Total Failure"
    breakdown.append(total)

    if probs["bestial"] != 0:
        bestial = roll.dicemoji.emojify_die(1, True) + f"{probs['bestial']:.2%} Bestial Failure"
        breakdown.append(bestial)

    embed.add_field(name="Breakdown", value="\n".join(breakdown))

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
        outcome = Roll(params.pool, params.hunger, params.difficulty)

        # Check reroll options
        if strategy is not None:
            if strategy == "reroll_failures" and outcome.can_reroll_failures:
                outcome.reroll(strategy)
            elif strategy == "maximize_criticals" and outcome.can_maximize_criticals:
                outcome.reroll(strategy)
            elif strategy == "avoid_messy" and outcome.can_avoid_messy_critical:
                outcome.reroll(strategy)
            elif strategy == "risky" and outcome.can_risky_messy_critical:
                outcome.reroll(strategy)

        totals["total_successes"] += outcome.total_successes
        totals["margin"] += outcome.margin
        outcomes[outcome.outcome] += 1

    probabilities = defaultdict(lambda: 0)
    probabilities["total_successes"] = totals["total_successes"] / trials
    probabilities["margin"] = totals["margin"] / trials

    for outcome, frequency in outcomes.items():
        probabilities[outcome] = frequency / trials

    return probabilities
