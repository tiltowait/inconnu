"""reference/probabilities.py - Calculate the probability of a given roll."""

from collections import defaultdict
from dataclasses import dataclass
from math import comb
from typing import NamedTuple

import discord

import errors
import services
import ui
from ctx import AppCtx
from inconnu import vr as roll
from models import VChar
from services.haven import Haven

HELP_URL = "https://docs.inconnu.app/command-reference/miscellaneous#probability-calculation"
STRATEGIES = {
    "reroll_failures": "Re-rolling Failures",
    "maximize_criticals": "Maximizing Crits",
    "avoid_messy": "Avoiding Messy Crits",
    "risky": "Riskily Avoiding Messy Crits",
}
DISPLAY_MIN = 0.00005  # Anything smaller displays as 0.00%
MAX_POOL = 100
MAX_REROLL = 3

# Category odds on a single die. Normal: failure (1-5), success (6-9), critical (10).
# Hunger: bestial (1), failure (2-5), success (6-9), critical (10).
NORMAL_ODDS = (0.5, 0.4, 0.1)
HUNGER_ODDS = (0.1, 0.4, 0.4, 0.1)


class RollParams(NamedTuple):
    """The parameters of the roll whose probabilities are being calculated."""

    pool: int
    hunger: int
    difficulty: int


@dataclass
class Probabilities:
    """The probability of each roll outcome, plus average successes and margin."""

    critical: float = 0.0
    success: float = 0.0
    messy: float = 0.0
    fail: float = 0.0
    total_fail: float = 0.0
    bestial: float = 0.0
    total_successes: float = 0.0
    margin: float = 0.0


async def probability(
    ctx: AppCtx,
    syntax: str,
    strategy: str | None = None,
    char_name: str | None = None,
):
    """Calculate the probabilities surrounding a roll."""
    character = None
    try:
        if roll.needs_character(syntax):
            if ctx.guild is None:
                await ctx.respond("Sorry, you can't use traits in DMs.")
                return

            syntax = " ".join(syntax.split())
            haven = Haven(
                ctx,
                character=char_name,
                tip=f"`/probability` `roll:{syntax}` `character:CHARACTER`",
                char_filter=lambda c: _can_roll(c, syntax),
                errmsg=f"None of your characters can roll `{syntax}`.",
                help=HELP_URL,
            )
            character = await haven.fetch()

        parser = roll.RollParser(character, syntax)
        params = RollParams(parser.pool, parser.hunger, parser.difficulty)
        probabilities = calculate(*params, strategy)

        await __display_embed(ctx, params, strategy, probabilities)

    except (SyntaxError, ValueError, errors.TraitError) as err:
        await ui.embeds.error(ctx, err, character=character, help_url=HELP_URL)


def _can_roll(character: VChar, syntax: str):
    """Raise an exception if the character can't roll the syntax."""
    roll.RollParser(character, syntax)


async def __display_embed(
    ctx: AppCtx, params: RollParams, strategy: str | None, probs: Probabilities
):
    """Display the probabilities in a nice embed."""
    uncomplicated = probs.success + probs.critical
    description = f"**{uncomplicated:.2%}** success without complication"
    description += f"\n**{probs.total_successes:.2f}** average successes"
    description += f"\n**{probs.margin:.2f}** average margin"

    if strategy is not None:
        description = f"**{STRATEGIES[strategy]}**\n\n{description}"

    embed = discord.Embed(
        title=f"Pool {params.pool} | Hunger {params.hunger} | DC {params.difficulty}",
        description=description,
        colour=0x000000,
    )
    embed.set_author(name="Outcome Probabilities")

    # Breakdown field

    # We show the following fields in this order:
    # Critical (Opt)
    # Success - Technically optional, but we will always show it
    # Messy (Opt)
    # ---
    # Failure (Opt)
    # Total Faiiure
    # Bestial (Opt)

    can_emoji = await services.settings.can_emoji(ctx)
    breakdown = []

    if probs.critical >= DISPLAY_MIN:
        crit = roll.dicemoji.emojify_die(10, False) if can_emoji else ""
        crit += f"{probs.critical:.2%} Critical Win"
        breakdown.append(crit)

    success = roll.dicemoji.emojify_die(6, False) if can_emoji else ""
    success += f"{probs.success:.2%} Success"
    breakdown.append(success)

    if probs.messy >= DISPLAY_MIN:
        messy = roll.dicemoji.emojify_die(10, True) if can_emoji else ""
        messy += f"{probs.messy:.2%} Messy Critical"
        breakdown.append(messy)

    breakdown.append("------")

    if probs.fail >= DISPLAY_MIN:
        # Only show regular failure if there's a distinction between it and total failure
        fail = roll.dicemoji.emojify_die(3, False) if can_emoji else ""
        fail += f"{probs.fail:.2%} Failure"
        breakdown.append(fail)

    total = roll.dicemoji.emojify_die(3, True) if can_emoji else ""
    total += f"{probs.total_fail:.2%} Total Failure"
    breakdown.append(total)

    if probs.bestial >= DISPLAY_MIN:
        bestial = roll.dicemoji.emojify_die(1, True) if can_emoji else ""
        bestial += f"{probs.bestial:.2%} Bestial Failure"
        breakdown.append(bestial)

    embed.add_field(name="Breakdown", value="\n".join(breakdown))

    await ctx.respond(embed=embed)


def calculate(
    pool: int, hunger: int, difficulty: int, strategy: str | None = None
) -> Probabilities:
    """Calculate the exact probability of each outcome, plus average successes and margin.

    Mirrors inconnu.Roll: pool includes hunger, and the reroll strategy is applied
    whenever the Roll's corresponding can_* check would allow it."""
    if not 0 <= hunger <= 5:
        raise ValueError(f"Hunger must be between 0 and 5. (Got `{hunger}`.)")
    if difficulty < 0:
        raise ValueError(f"Difficulty cannot be less than 0. (Got `{difficulty}`.)")
    pool = max(1, pool)
    if pool > MAX_POOL:
        raise ValueError(f"Pool cannot exceed {MAX_POOL}. (Got `{pool}`.)")

    normal_count = max(0, pool - hunger)
    hunger_count = min(pool, hunger)

    # Rerolled dice are normal dice, so their outcomes are drawn from the normal odds
    rerolls = [_distribution(k, NORMAL_ODDS) for k in range(MAX_REROLL + 1)]

    # We only care whether hunger dice contain *any* ones, so we collapse those states
    hunger_states = defaultdict(float)
    for (ones, _, succ, tens), prob in _distribution(hunger_count, HUNGER_ODDS):
        hunger_states[(ones > 0, succ, tens)] += prob

    probs = Probabilities()
    for (fails, succ, tens), normal_prob in _distribution(normal_count, NORMAL_ODDS):
        for (bestial, h_succ, h_tens), hunger_prob in hunger_states.items():
            prob = normal_prob * hunger_prob
            hunger_state = (bestial, h_succ, h_tens, hunger_count)

            if strategy is None or not _can_reroll(
                strategy, fails, succ, tens, hunger_state, difficulty
            ):
                _tally(probs, succ, tens, hunger_state, difficulty, prob)
                continue

            kept_succ, kept_tens, rerolled = _reroll(strategy, fails, succ, tens)
            for (_, new_succ, new_tens), reroll_prob in rerolls[rerolled]:
                _tally(
                    probs,
                    kept_succ + new_succ,
                    kept_tens + new_tens,
                    hunger_state,
                    difficulty,
                    prob * reroll_prob,
                )

    probs.margin = probs.total_successes - difficulty
    return probs


def _distribution(count: int, odds: tuple[float, ...]) -> list[tuple[tuple[int, ...], float]]:
    """Every way count dice can fall into the categories given by odds, with probabilities."""
    if len(odds) == 1:
        return [((count,), odds[0] ** count)]

    states = []
    for first in range(count + 1):
        first_prob = comb(count, first) * odds[0] ** first
        for rest, rest_prob in _distribution(count - first, odds[1:]):
            states.append(((first, *rest), first_prob * rest_prob))

    return states


def _total_successes(succ: int, tens: int, h_succ: int, h_tens: int) -> int:
    """Total successes, counting each pair of tens as four."""
    all_tens = tens + h_tens
    return succ + h_succ + all_tens + all_tens - all_tens % 2


def _tally(
    probs: Probabilities,
    succ: int,
    tens: int,
    hunger_state: tuple,
    difficulty: int,
    prob: float,
):
    """Add a final dice state's probability to its outcome and to the success average."""
    bestial, h_succ, h_tens, _ = hunger_state
    total = _total_successes(succ, tens, h_succ, h_tens)
    probs.total_successes += prob * total

    if total >= difficulty and total > 0:
        if tens + h_tens < 2:
            probs.success += prob
        elif h_tens > 0:
            probs.messy += prob
        else:
            probs.critical += prob
    elif bestial:
        probs.bestial += prob
    elif total > 0:
        probs.fail += prob
    else:
        probs.total_fail += prob


def _can_reroll(
    strategy: str, fails: int, succ: int, tens: int, hunger_state: tuple, difficulty: int
) -> bool:
    """Whether the strategy can be applied. Mirrors Roll's can_* properties."""
    _, h_succ, h_tens, hunger_count = hunger_state
    normal_count = fails + succ + tens

    if strategy == "reroll_failures":
        return fails > 0

    if strategy == "maximize_criticals":
        if normal_count + hunger_count < 2:
            return False
        if normal_count == 1:
            return tens == 0 and h_tens > 0
        return tens != normal_count

    # avoid_messy and risky both require a messy critical with exactly one hunger ten
    total = _total_successes(succ, tens, h_succ, h_tens)
    messy = tens + h_tens >= 2 and h_tens > 0 and total >= difficulty and total > 0
    can_avoid = messy and h_tens == 1 and tens <= 3

    if strategy == "avoid_messy":
        return can_avoid
    return can_avoid and fails > 0  # risky


def _reroll(strategy: str, fails: int, succ: int, tens: int) -> tuple[int, int, int]:
    """Apply a strategy to normal dice. Returns kept successes, kept tens, and dice rerolled.

    Mirrors the reroll helpers in inconnu.roll.roll."""
    if strategy == "reroll_failures":
        return succ, tens, min(fails, MAX_REROLL)

    if strategy == "maximize_criticals":
        rerolled_fails = min(fails, MAX_REROLL)
        rerolled_succ = min(succ, MAX_REROLL - rerolled_fails)
        return succ - rerolled_succ, tens, rerolled_fails + rerolled_succ

    if strategy == "avoid_messy":
        rerolled_tens = min(tens, MAX_REROLL)
        return succ, tens - rerolled_tens, rerolled_tens

    # risky: all tens (at most three, per can_avoid_messy_critical) plus failures to make three
    rerolled_fails = min(fails, MAX_REROLL - tens)
    return succ, 0, tens + rerolled_fails
