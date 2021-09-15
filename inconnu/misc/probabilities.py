"""misc/probabilities.py - Calculate the probability of a given roll."""

import os
from collections import defaultdict

import pymongo

from .. import common
from .. import roll
from ..vchar import errors, VChar


async def process(ctx, syntax: str, character=None):
    """Calculate the probabilities surrounding a roll."""
    if roll.needs_character(syntax):
        try:
            character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

        except errors.UnspecifiedCharacterError as err:
            tip = f"`/probability` `syntax:{syntax}` `character:CHARACTER`"
            character = await common.select_character(ctx, err, ("Proper syntax", tip))

            if character is None:
                # They didn't select a character
                return
        except errors.CharacterError as err:
            await common.display_error(ctx, ctx.author.display_name, err)
            return
    else:
        character = None

    try:
        args = syntax.split()
        pool_str, params = roll.prepare_roll(character, *args)
        probabilities = __get_probabilities(params)

        await ctx.respond(str(probabilities))

    except (SyntaxError, ValueError) as err:
        name = character.name if character is not None else ctx.author.display_name
        await common.display_error(ctx, name, str(err))


def __get_probabilities(params):
    """Retrieve the probabilities from storage or, if not calculated yet, generate them."""
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    col = client.inconnu.probabilities

    probs = col.find_one({
        "pool": params.pool,
        "hunger": params.hunger,
        "difficulty": params.difficulty
    })

    if probs is None:
        probs = __simulate(params)

        # Save the probabilities
        col.insert_one({
            "pool": params.pool,
            "hunger": params.hunger,
            "difficulty": params.difficulty,
            "probabilities": probs
        })

    client.close()
    return probs


def __simulate(params):
    """Simulate 1000 rolls and calculate the probabilities of each potential outcome."""
    trials = 10000
    totals = defaultdict(lambda: 0)
    outcomes = defaultdict(lambda: 0)

    for _ in range(trials):
        outcome = roll.roll_pool(params)

        totals["total_successes"] += outcome.total_successes
        totals["margin"] += outcome.margin
        outcomes[outcome.outcome] += 1

    probabilities = {}
    probabilities["successes"] = totals["successes"] / trials
    probabilities["margin"] = totals["margin"] / trials

    for outcome, frequency in outcomes.items():
        probabilities[outcome] = frequency / trials

    return probabilities
