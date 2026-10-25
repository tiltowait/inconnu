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
from inconnu.roll import Strategy
from models import IMPAIRMENT_DICE, Impairment, ImpairmentCategory, VChar
from services.haven import Haven

HELP_URL = "https://docs.inconnu.app/command-reference/miscellaneous#probability-calculation"
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
    strategy_name: str | None = None,
    char_name: str | None = None,
    impairment_category: ImpairmentCategory | None = None,
):
    """Calculate the probabilities surrounding a roll, including any Impairment
    penalty the roll would receive."""
    character = None
    try:
        strategy = Strategy(strategy_name) if strategy_name is not None else None

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
        penalty = await roll.impairment_penalty(
            ctx, character, parser.pool_str, impairment_category
        )
        pool = parser.pool - IMPAIRMENT_DICE if penalty else parser.pool
        params = RollParams(pool, parser.hunger, parser.difficulty)
        probabilities = calculate(*params, strategy)

        await __display_embed(ctx, params, strategy, probabilities, penalty)

    except (SyntaxError, ValueError, errors.TraitError) as err:
        await ui.embeds.error(ctx, err, character=character, help_url=HELP_URL)


def _can_roll(character: VChar, syntax: str):
    """Raise an exception if the character can't roll the syntax."""
    roll.RollParser(character, syntax)


async def __display_embed(
    ctx: AppCtx,
    params: RollParams,
    strategy: Strategy | None,
    probs: Probabilities,
    penalty: Impairment,
):
    """Display the probabilities in a nice embed."""
    uncomplicated = probs.success + probs.critical
    description = f"**{uncomplicated:.2%}** success without complication"
    description += f"\n**{probs.total_successes:.2f}** average successes"
    description += f"\n**{probs.margin:.2f}** average margin"

    notes = []
    if strategy is not None:
        notes.append(f"**{strategy.description}**")
    if penalty:
        notes.append(f"*Includes -{IMPAIRMENT_DICE} ({penalty.description} impairment)*")
    if notes:
        description = "\n".join(notes) + f"\n\n{description}"

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


# Probability calculation
#
# We originally calculated outcome probabilities via 10k simulated rolls using
# real Roll objects. In the name of consistency, these outcomes were persisted
# to a database collection.
#
# Simulated rolls are "close enough", but are off by ~1%, and the whole
# implementation was slow: either because we had to roll a bunch, or because
# we had to fetch from the database.
#
# The below implementation uses combinatorics to calculate exact probabilities.
#
# Overview
#
# A roll's outcome doesn't depend on exact faces, only on how many dice land in
# each category. Normal dice: failure (1-5), success (6-9), or ten. Hunger dice:
# one, failure (2-5), success (6-9), or ten. Rather than enumerate 10^pool face
# combinations, we enumerate category counts and weight each by its multinomial
# probability.
#
# 1. Hunger states. We enumerate every hunger dice result, collapsed to (any
#    ones?, successes, tens), since the number of ones doesn't matter.
# 2. Normal grid. grid[tens][successes] holds the probability of each normal
#    dice result. Failures are implied by the remaining dice.
# 3. Rerolls. A strategy rerolls at most three normal dice, so each rerollable
#    cell's probability is redistributed over the (at most 10) ways the rerolled
#    dice can land. Whether a cell may reroll sometimes depends on the hunger
#    dice, but only a small part of them (see _group_key()). Hunger states that
#    look the same to the reroll check share one post-reroll grid, so we build a
#    handful of grids rather than one per hunger state. Avoid Messy and Risky
#    can only reroll with three or fewer normal tens, so only those rows of the
#    grid are rebuilt.
# 4. Scoring. For each hunger state, we walk the grid's tens rows. Within a
#    row, everything but normal successes is fixed, so suffix sums over
#    successes tell us in one lookup how much of the row meets the difficulty.
#    That mass is a success, critical, or messy critical (depending on tens);
#    the rest is a failure, total failure, or bestial failure (depending on
#    hunger ones).
#
# The logic intentionally mirrors Roll, and tests verify the two agree exactly
# across every hunger, difficulty, and strategy combination for pools up to 5.
# (Test time is exponential as pool size increases. Because 5 is sufficient to
# cover every edge case, there is no value in testing larger pools.)
#
# Benchmark (pool 100, DC 4; Python 3.13, Apple M1 Pro)
#
#   Strategy              Hunger 5    Hunger 0
#   None                    2.4 ms      1.6 ms
#   Re-roll Failures        5.5 ms      5.1 ms
#   Maximize Crits          6.2 ms      5.8 ms
#   Avoid Messy             6.6 ms      1.8 ms
#   Risky                   6.9 ms      1.8 ms
#
# Typical pools (15 dice or fewer) take under half a millisecond.


def calculate(
    pool: int, hunger: int, difficulty: int, strategy: Strategy | None = None
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

    # We only care whether hunger dice contain *any* ones, so we collapse those states
    hunger_states = defaultdict(float)
    for (ones, _, succ, tens), prob in _distribution(hunger_count, HUNGER_ODDS):
        hunger_states[(ones > 0, succ, tens)] += prob

    # Reroll checks only see part of the hunger dice, so hunger states that look the
    # same to the check share a single post-reroll grid
    groups = defaultdict(list)
    for state, prob in hunger_states.items():
        groups[_group_key(strategy, normal_count, state)].append((state, prob))

    base = _normal_grid(normal_count)
    probs = Probabilities()
    for members in groups.values():
        if strategy is None:
            grid = base
        else:
            bestial, h_succ, h_tens = members[0][0]
            hunger_state = (bestial, h_succ, h_tens, hunger_count)
            grid = _post_reroll(base, strategy, hunger_state, difficulty)
        _score(probs, grid, members, difficulty)

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


def _normal_grid(count: int) -> list[list[float]]:
    """The probability of each normal dice result, indexed as grid[tens][successes].

    Here, successes are 6-9 only. Failures are whatever dice remain."""
    fail_odds, succ_odds, ten_odds = NORMAL_ODDS
    grid = [[0.0] * (count + 1) for _ in range(count + 1)]
    for tens in range(count + 1):
        tens_prob = comb(count, tens) * ten_odds**tens
        for succ in range(count - tens + 1):
            fails = count - tens - succ
            grid[tens][succ] = tens_prob * comb(count - tens, succ) * succ_odds**succ
            grid[tens][succ] *= fail_odds**fails

    return grid


def _group_key(strategy: Strategy | None, normal_count: int, hunger_state: tuple):
    """The part of a hunger state the strategy's reroll check depends on."""
    _, h_succ, h_tens = hunger_state

    match strategy:
        case Strategy.AVOID_MESSY | Strategy.RISKY:
            # Messy crits are only avoidable with one hunger ten; success depends on h_succ
            return (h_succ, h_tens) if h_tens == 1 else None
        case Strategy.MAXIMIZE_CRITICALS if normal_count == 1:
            return h_tens > 0
        case _:
            return None


def _post_reroll(
    base: list[list[float]], strategy: Strategy, hunger_state: tuple, difficulty: int
) -> list[list[float]]:
    """The normal dice grid after applying the strategy wherever the roll allows it."""
    count = len(base) - 1
    rerolls = [_distribution(k, NORMAL_ODDS) for k in range(MAX_REROLL + 1)]

    # Rows that can't reroll are unchanged, so we only rebuild the ones that can
    rows = _rerollable_rows(strategy, count)
    grid = [row.copy() for row in base]
    for tens in rows:
        grid[tens] = [0.0] * (count + 1)

    for tens in rows:
        for succ in range(count - tens + 1):
            prob = base[tens][succ]
            fails = count - tens - succ

            if not _can_reroll(strategy, fails, succ, tens, hunger_state, difficulty):
                grid[tens][succ] += prob
                continue

            kept_succ, kept_tens, rerolled = _reroll(strategy, fails, succ, tens)
            for (_, new_succ, new_tens), reroll_prob in rerolls[rerolled]:
                grid[kept_tens + new_tens][kept_succ + new_succ] += prob * reroll_prob

    return grid


def _rerollable_rows(strategy: Strategy, count: int) -> range:
    """The numbers of normal tens with which the strategy can possibly reroll."""
    match strategy:
        case Strategy.AVOID_MESSY | Strategy.RISKY:
            # Avoiding a messy critical requires no more than three normal tens
            return range(min(count, MAX_REROLL) + 1)
        case _:
            return range(count + 1)


def _score(probs: Probabilities, grid: list[list[float]], members: list, difficulty: int):
    """Add each hunger state's outcomes, given the normal dice grid it's rolled with."""
    count = len(grid) - 1

    # tails[tens][succ] is the probability of that many tens and at least succ successes
    tails = []
    avg_succ = 0.0
    for row in grid:
        tail = [0.0] * (count + 2)
        for succ in range(count, -1, -1):
            tail[succ] = tail[succ + 1] + row[succ]
            avg_succ += succ * row[succ]
        tails.append(tail)

    target = max(difficulty, 1)
    for (bestial, h_succ, h_tens), hunger_prob in members:
        avg_total = avg_succ
        for tens, tail in enumerate(tails):
            mass = tail[0]
            if mass == 0.0:
                continue

            # Successes from everything except normal 6-9s
            all_tens = tens + h_tens
            other = h_succ + 2 * all_tens - all_tens % 2
            avg_total += mass * other

            needed = target - other
            hit = mass if needed <= 0 else tail[min(needed, count + 1)]
            miss = mass - hit

            if all_tens < 2:
                probs.success += hunger_prob * hit
            elif h_tens > 0:
                probs.messy += hunger_prob * hit
            else:
                probs.critical += hunger_prob * hit

            if bestial:
                probs.bestial += hunger_prob * miss
            elif other == 0:
                # No successes at all is only possible without normal 6-9s
                zero = grid[tens][0]
                probs.total_fail += hunger_prob * zero
                probs.fail += hunger_prob * (miss - zero)
            else:
                probs.fail += hunger_prob * miss

        probs.total_successes += hunger_prob * avg_total


def _can_reroll(
    strategy: Strategy, fails: int, succ: int, tens: int, hunger_state: tuple, difficulty: int
) -> bool:
    """Whether the strategy can be applied. Mirrors Roll's can_* properties."""
    _, h_succ, h_tens, hunger_count = hunger_state
    normal_count = fails + succ + tens

    match strategy:
        case Strategy.REROLL_FAILURES:
            return fails > 0

        case Strategy.MAXIMIZE_CRITICALS:
            if normal_count + hunger_count < 2:
                return False
            if normal_count == 1:
                return tens == 0 and h_tens > 0
            return tens != normal_count

        case Strategy.AVOID_MESSY:
            return _can_avoid_messy(succ, tens, h_succ, h_tens, difficulty)

        case Strategy.RISKY:
            return fails > 0 and _can_avoid_messy(succ, tens, h_succ, h_tens, difficulty)


def _total_successes(succ: int, tens: int, h_succ: int, h_tens: int) -> int:
    """Total successes, counting each pair of tens as four."""
    all_tens = tens + h_tens
    return succ + h_succ + all_tens + all_tens - all_tens % 2


def _can_avoid_messy(succ: int, tens: int, h_succ: int, h_tens: int, difficulty: int) -> bool:
    """Whether the roll is a messy critical with exactly one hunger ten and few normal tens."""
    total = _total_successes(succ, tens, h_succ, h_tens)
    messy = tens + h_tens >= 2 and h_tens > 0 and total >= difficulty and total > 0
    return messy and h_tens == 1 and tens <= 3


def _reroll(strategy: Strategy, fails: int, succ: int, tens: int) -> tuple[int, int, int]:
    """Apply a strategy to normal dice. Returns kept successes, kept tens, and dice rerolled.

    Mirrors the reroll helpers in inconnu.roll.roll."""
    match strategy:
        case Strategy.REROLL_FAILURES:
            return succ, tens, min(fails, MAX_REROLL)

        case Strategy.MAXIMIZE_CRITICALS:
            rerolled_fails = min(fails, MAX_REROLL)
            rerolled_succ = min(succ, MAX_REROLL - rerolled_fails)
            return succ - rerolled_succ, tens, rerolled_fails + rerolled_succ

        case Strategy.AVOID_MESSY:
            rerolled_tens = min(tens, MAX_REROLL)
            return succ, tens - rerolled_tens, rerolled_tens

        case Strategy.RISKY:
            # All tens (at most three, per _can_avoid_messy) plus failures to make three
            rerolled_fails = min(fails, MAX_REROLL - tens)
            return succ, 0, tens + rerolled_fails
