"""Tests for inconnu/reference/probabilities.py."""

import time
from collections.abc import Iterator
from dataclasses import asdict
from itertools import combinations_with_replacement
from math import factorial
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import inconnu
from ctx import AppCtx
from inconnu.reference.probabilities import Strategy, calculate, probability
from inconnu.roll.dicethrow import DiceThrow
from models import ImpairmentCategory, VChar
from tests.characters import gen_char

# Representative faces and their odds. Faces within a category behave identically.
_NORMAL_FACES = ((1, 0.5), (6, 0.4), (10, 0.1))
_HUNGER_FACES = ((1, 0.1), (2, 0.4), (6, 0.4), (10, 0.1))
_STRATEGIES = (None, *Strategy)
_CHECKS = {
    Strategy.REROLL_FAILURES: "can_reroll_failures",
    Strategy.MAXIMIZE_CRITICALS: "can_maximize_criticals",
    Strategy.AVOID_MESSY: "can_avoid_messy_critical",
    Strategy.RISKY: "can_risky_messy_critical",
}
_OUTCOMES = ("critical", "success", "messy", "fail", "total_fail", "bestial")
_KEYS = (*_OUTCOMES, "total_successes", "margin")


def _states(faces: tuple, count: int):
    """Yield one dice list per distinct category-count combination, with its probability."""
    for combo in combinations_with_replacement(faces, count):
        prob = factorial(count)
        for face in faces:
            prob /= factorial(combo.count(face))
        for _, odds in combo:
            prob *= odds
        yield [face for face, _ in combo], prob


def _make_roll(normal: list[int], hunger: list[int], difficulty: int) -> inconnu.Roll:
    """Create a Roll with predetermined dice."""
    roll = inconnu.Roll(1, 0, difficulty)
    roll.normal = DiceThrow(list(normal))
    roll.hunger = DiceThrow(list(hunger))
    return roll


def _reference(pool: int, hunger: int, difficulty: int, strategy: Strategy | None) -> dict:
    """Calculate exact probabilities by evaluating real Roll objects."""
    probs = dict.fromkeys(_KEYS, 0.0)
    queue = []
    calls = []

    def fake_d10(count: int | None = None) -> int | list[int]:
        """Supply queued reroll faces (or 1 if none), recording each reroll request."""
        if count is not None:
            return [1] * count  # Roll.__init__; its dice get replaced anyway
        calls.append(None)
        return queue.pop(0) if queue else 1

    with patch("inconnu.d10", new=fake_d10):
        for normal, normal_prob in _states(_NORMAL_FACES, pool - hunger):
            for hunger_dice, hunger_prob in _states(_HUNGER_FACES, hunger):
                prob = normal_prob * hunger_prob
                roll = _make_roll(normal, hunger_dice, difficulty)
                outcomes = [(roll, prob)]

                if strategy is not None and getattr(roll, _CHECKS[strategy]):
                    calls.clear()
                    _make_roll(normal, hunger_dice, difficulty).reroll(strategy)
                    rerolled = len(calls)
                    outcomes = []
                    for faces, reroll_prob in _states(_NORMAL_FACES, rerolled):
                        queue[:] = faces
                        roll = _make_roll(normal, hunger_dice, difficulty)
                        roll.reroll(strategy)
                        outcomes.append((roll, prob * reroll_prob))

                for roll, prob in outcomes:
                    probs[roll.outcome] += prob
                    probs["total_successes"] += prob * roll.total_successes
                    probs["margin"] += prob * roll.margin

    return probs


@pytest.mark.parametrize("strategy", _STRATEGIES)
def test_calculate_matches_roll(strategy: Strategy | None):
    """Test calculate() agrees exactly with Roll across small pools, hunger, and difficulty."""
    for pool in range(1, 6):
        for hunger in range(pool + 1):
            for difficulty in range(10):
                expected = _reference(pool, hunger, difficulty, strategy)
                actual = calculate(pool, hunger, difficulty, strategy)
                params = (pool, hunger, difficulty, strategy)
                assert asdict(actual) == pytest.approx(expected), params


@pytest.mark.parametrize("strategy", _STRATEGIES)
def test_calculate_outcomes_sum_to_one(strategy: Strategy | None):
    """Test outcome probabilities are exhaustive for a large pool."""
    probs = calculate(30, 5, 8, strategy)
    assert sum(getattr(probs, outcome) for outcome in _OUTCOMES) == pytest.approx(1.0)


def test_calculate_hunger_exceeding_pool():
    """Test hunger greater than the pool is capped to the pool, as in Roll."""
    assert asdict(calculate(2, 4, 1)) == pytest.approx(asdict(calculate(2, 2, 1)))


def test_calculate_huge_pool_is_fast():
    """Test a maximum-size pool with a reroll strategy completes quickly."""
    start = time.perf_counter()
    calculate(100, 5, 20, Strategy.MAXIMIZE_CRITICALS)
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize(
    "pool,hunger,difficulty",
    [(101, 0, 1), (5, 6, 1), (5, -1, 1), (5, 0, -1)],
)
def test_calculate_invalid_parameters(pool: int, hunger: int, difficulty: int):
    """Test calculate() rejects the same parameters Roll does."""
    with pytest.raises(ValueError):
        inconnu.Roll(pool, hunger, difficulty)
    with pytest.raises(ValueError):
        calculate(pool, hunger, difficulty)


# Impairment


@pytest.fixture
def impaired_vampire() -> VChar:
    """A physically impaired vampire with a 5-dice physical pool."""
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 2})
    char.health = "/" * len(char.health)
    return char


@pytest.fixture
def ctx() -> AppCtx:
    """A guild context that records what it sends."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.respond = AsyncMock()
    return ctx


@pytest.fixture
def mock_settings() -> Iterator[None]:
    """Auto-impairment on; text instead of emoji."""
    with (
        patch("services.settings.auto_impairment", new_callable=AsyncMock, return_value=True),
        patch("services.settings.can_emoji", new_callable=AsyncMock, return_value=False),
    ):
        yield


@pytest.fixture
def mock_haven(impaired_vampire: VChar) -> Iterator[MagicMock]:
    """Make the character lookup return the impaired vampire."""
    haven = MagicMock()
    haven.fetch = AsyncMock(return_value=impaired_vampire)
    with patch("inconnu.reference.probabilities.Haven", return_value=haven) as mock:
        yield mock


def sent_embed(ctx: AppCtx) -> discord.Embed:
    """The embed the command responded with."""
    call = cast(AsyncMock, ctx.respond).await_args
    assert call is not None
    return call.kwargs["embed"]


@pytest.mark.usefixtures("mock_settings", "mock_haven")
async def test_probability_applies_impairment(ctx: AppCtx):
    """The odds are for the penalized pool, and the penalty is shown."""
    await probability(ctx, "strength+brawl 0 1")
    embed = sent_embed(ctx)

    assert embed.title == "Pool 3 | Hunger 0 | DC 1"
    assert embed.description is not None
    assert embed.description.startswith("*Includes -2 (physical impairment)*\n\n")


@pytest.mark.usefixtures("mock_settings", "mock_haven")
async def test_probability_ignores_impairment(ctx: AppCtx):
    """Ignoring Impairment shows the odds for the full pool."""
    await probability(ctx, "strength+brawl 0 1", impairment_category=ImpairmentCategory.IGNORE)
    embed = sent_embed(ctx)

    assert embed.title == "Pool 5 | Hunger 0 | DC 1"
    assert embed.description is not None
    assert "impairment" not in embed.description


@pytest.mark.usefixtures("mock_settings", "mock_haven")
async def test_probability_impairment_with_strategy(ctx: AppCtx):
    """The penalty is listed under the reroll strategy."""
    await probability(ctx, "strength+brawl 0 1", "reroll_failures")
    embed = sent_embed(ctx)

    assert embed.description is not None
    expected = (
        f"**{Strategy.REROLL_FAILURES.description}**\n*Includes -2 (physical impairment)*\n\n"
    )
    assert embed.description.startswith(expected)
