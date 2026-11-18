"""Frenzy check tests."""

from collections.abc import Callable, Iterator
from unittest.mock import AsyncMock, patch

import pytest

from ctx import AppCtx
from inconnu.misc.frenzy import FrenzyAdvantage, FrenzyPenalty, frenzy, frenzy_roll
from models.vchar import VChar


@pytest.fixture(autouse=True)
def mock_display() -> Iterator[None]:
    """Show the outcome as an embed, without sending anything."""
    with (
        patch("services.settings.accessible", new_callable=AsyncMock, return_value=False),
        patch("ctx.AppCtx.respond", new_callable=AsyncMock),
        patch("inconnu.misc.frenzy.get_message", new_callable=AsyncMock),
    ):
        yield


@pytest.mark.parametrize(
    "die,difficulty,title,color",
    [
        (6, 1, "Frenzy Success", None),
        (5, 1, "Frenzy Failure", 0x880000),  # No successes
        (6, 10, "Frenzy Failure", 0x880000),  # Some successes, but not enough
    ],
)
async def test_frenzy_report(
    die: int,
    difficulty: int,
    title: str,
    color: int | None,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Every failure, including one with no successes, is reported in red."""
    with patch("inconnu.d10", side_effect=lambda count: [die] * count):
        await frenzy(ctx, vamp, difficulty, None, None)

    passed = title == "Frenzy Success"
    assert vamp.log.times_frenzied == int(not passed)
    assert vamp.log.frenzy_resisted == int(passed)
    assert mock_common_report.await_args is not None
    kwargs = mock_common_report.await_args.kwargs
    assert kwargs["title"] == title
    assert kwargs["color"] == color


def fixed_dice(die: int, reroll=10) -> Callable[[int | None], int | list[int]]:
    """A d10 that throws the same face, and another on re-rolls."""

    def d10(count: int | None = None) -> int | list[int]:
        """Throw the dice."""
        return reroll if count is None else [die] * count

    return d10


@pytest.mark.parametrize(
    "penalty,bonus,advantages,change",
    [
        (None, 0, [], 0),
        (None, 3, [], 3),
        (None, 0, [FrenzyAdvantage.GENTLE_MIND], 4),
        (None, 0, [FrenzyAdvantage.THE_DREAM], 0),
        (None, 2, [FrenzyAdvantage.COLD_DEAD_HUNGER, FrenzyAdvantage.JEWEL_IN_THE_GARDEN], 8),
        ("malkavian", 0, [], -2),
        ("malkavian", 1, [FrenzyAdvantage.THE_HEART_OF_DARKNESS], 1),
    ],
)
def test_frenzy_pool(
    vamp: VChar,
    penalty: FrenzyPenalty | None,
    bonus: int,
    advantages: list[FrenzyAdvantage],
    change: int,
):
    """Penalties, bonus dice, and advantages combine in the pool."""
    with patch("inconnu.d10", side_effect=fixed_dice(6)):
        outcome = frenzy_roll(vamp, 1, penalty, bonus, advantages)

    assert outcome.pool == vamp.frenzy_resist + change
    assert outcome.dice == [6] * outcome.pool


@pytest.mark.parametrize("penalty", ["brujah", "malkavian"])
def test_frenzy_penalty_floor(vamp: VChar, penalty: FrenzyPenalty):
    """A penalty leaves at least one die, before bonuses."""
    vamp.willpower = "/////"  # No Willpower left
    vamp.humanity = 2
    vamp.potency = 3

    with patch("inconnu.d10", side_effect=fixed_dice(6)):
        outcome = frenzy_roll(vamp, 1, penalty, 2, [])

    assert outcome.pool == 3


def test_frenzy_duplicate_powers(vamp: VChar):
    """An advantage counts once, however often it's given."""
    with patch("inconnu.d10", side_effect=fixed_dice(6)):
        outcome = frenzy_roll(vamp, 1, None, 0, [FrenzyAdvantage.GENTLE_MIND] * 2)

    assert outcome.pool == vamp.frenzy_resist + 4


@pytest.mark.parametrize("dream", [True, False])
def test_frenzy_the_dream(vamp: VChar, dream: bool):
    """The Dream re-rolls up to three failures, keeping the original faces."""
    advantages = [FrenzyAdvantage.THE_DREAM] if dream else []
    with patch("inconnu.d10", side_effect=fixed_dice(1, reroll=7)):
        outcome = frenzy_roll(vamp, 3, None, 0, advantages)

    pool = vamp.frenzy_resist
    assert pool > 3
    if dream:
        assert outcome.original == [1] * pool
        assert outcome.dice == [7, 7, 7] + [1] * (pool - 3)
        assert outcome.passed
    else:
        assert outcome.original is None
        assert outcome.dice == [1] * pool
        assert not outcome.passed


@pytest.mark.parametrize(
    "die,passed,critical",
    [(10, True, True), (6, True, False), (5, False, False)],
)
def test_frenzy_outcome(vamp: VChar, die: int, passed: bool, critical: bool):
    """A pair of 10s resists frenzy without losing a turn."""
    with patch("inconnu.d10", side_effect=fixed_dice(die)):
        outcome = frenzy_roll(vamp, 1, None, 0, [])

    assert outcome.passed == passed
    assert outcome.critical == critical
    assert vamp.log.frenzy_resisted == int(passed)
    assert vamp.log.times_frenzied == int(not passed)


@pytest.mark.parametrize(
    "bonus,dice,advantages",
    [
        (None, 0, []),
        ("3", 3, []),
        ("Gentle Mind", 0, [FrenzyAdvantage.GENTLE_MIND]),
        ("The Dream", 0, [FrenzyAdvantage.THE_DREAM]),
    ],
)
async def test_frenzy_bonus_option(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_common_report: AsyncMock,
    bonus: str | None,
    dice: int,
    advantages: list[FrenzyAdvantage],
):
    """/frenzy's bonus option is either a number of dice or an advantage."""
    with patch("inconnu.misc.frenzy.frenzy_roll", wraps=frenzy_roll) as mock_roll:
        await frenzy(ctx, vamp, 1, None, bonus)

    mock_roll.assert_called_once_with(vamp, 1, None, dice, advantages)
