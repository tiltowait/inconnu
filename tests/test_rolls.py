"""Test basic roll logic."""

import pytest

import inconnu
from inconnu.roll.dicethrow import DiceThrow


def gen_roll(
    fails: int,
    suxx: int,
    tens: int,
    h_ones: int,
    h_fails: int,
    h_suxx: int,
    h_tens: int,
    difficulty: int,
) -> inconnu.Roll:
    """Generate a roll with the given parameters."""

    def dice(face: int, count: int) -> list[int]:
        """Make a number of dice with a given face."""
        return [face for _ in range(count)]

    roll = inconnu.Roll(1, 0, difficulty)
    roll.normal.dice = dice(5, fails) + dice(6, suxx) + dice(10, tens)
    roll.hunger.dice = dice(1, h_ones) + dice(5, h_fails) + dice(6, h_suxx) + dice(10, h_tens)

    return roll


# Roll outcome tests


def test_bestial_failure():
    """This roll should be a bestial failure."""
    roll = gen_roll(1, 2, 1, 1, 1, 1, 0, 5)

    assert roll.is_bestial
    assert roll.outcome == "bestial"
    assert roll.total_successes == 4
    assert roll.margin == -1

    assert not roll.is_total_failure
    assert not roll.is_failure
    assert not roll.is_successful
    assert not roll.is_critical
    assert not roll.is_messy


def test_total_failure():
    """This roll should be a total failure."""
    roll = gen_roll(1, 0, 0, 0, 0, 0, 0, 2)

    assert roll.is_total_failure
    assert not roll.is_failure
    assert roll.outcome == "total_fail"
    assert roll.total_successes == 0
    assert roll.margin == -2

    assert not roll.is_bestial
    assert not roll.is_successful
    assert not roll.is_messy
    assert not roll.is_critical


def test_failure():
    """This roll should be a simple failure."""
    roll = gen_roll(0, 1, 0, 0, 0, 0, 0, 2)

    assert roll.is_failure
    assert roll.outcome == "fail"
    assert roll.total_successes == 1
    assert roll.margin == -1

    assert not roll.is_total_failure
    assert not roll.is_bestial
    assert not roll.is_successful
    assert not roll.is_messy
    assert not roll.is_critical


def test_success():
    """This roll should be a plain success."""
    roll = gen_roll(0, 2, 1, 0, 0, 0, 0, 3)

    assert roll.is_successful
    assert roll.outcome == "success"
    assert roll.total_successes == 3
    assert roll.margin == 0

    assert not roll.is_bestial
    assert not roll.is_total_failure
    assert not roll.is_failure
    assert not roll.is_messy
    assert not roll.is_critical


def test_messy_critical():
    """This roll should be a messy critical."""
    roll = gen_roll(0, 0, 0, 1, 0, 0, 2, 3)

    assert roll.is_successful
    assert roll.is_messy
    assert roll.outcome == "messy"
    assert roll.total_successes == 4
    assert roll.margin == 1

    assert not roll.is_bestial
    assert not roll.is_total_failure
    assert not roll.is_failure
    assert not roll.is_critical

    # A messy critical is still messy if there are two normal 10s
    roll = gen_roll(0, 0, 4, 1, 0, 0, 1, 3)
    assert roll.is_messy
    assert roll.total_successes == 9
    assert roll.margin == 6


def test_critical():
    """This roll should be a critical success."""
    roll = gen_roll(0, 1, 3, 0, 0, 0, 0, 3)

    assert roll.is_successful
    assert roll.is_critical
    assert roll.outcome == "critical"
    assert roll.total_successes == 6
    assert roll.margin == 3

    assert not roll.is_bestial
    assert not roll.is_total_failure
    assert not roll.is_failure
    assert not roll.is_messy


# Roll opportunity tests


def test_can_reroll_failures():
    """Test the various reroll failure states."""
    roll = gen_roll(3, 0, 0, 0, 1, 1, 0, 3)
    assert roll.can_reroll_failures

    roll = gen_roll(0, 3, 0, 0, 1, 1, 0, 3)
    assert not roll.can_reroll_failures


def test_can_maximize_crits():
    """Test the maximize crits options."""
    roll = gen_roll(1, 1, 3, 0, 0, 0, 0, 3)
    assert roll.can_maximize_criticals

    roll = gen_roll(0, 0, 3, 0, 0, 0, 0, 3)
    assert not roll.can_maximize_criticals

    roll = gen_roll(0, 0, 0, 0, 0, 0, 3, 3)
    assert not roll.can_maximize_criticals


def test_can_avoid_messy():
    """Test the avoid messy options."""
    roll = gen_roll(0, 0, 1, 0, 0, 0, 1, 3)
    assert roll.is_messy
    assert roll.can_avoid_messy_critical

    roll = gen_roll(0, 0, 0, 0, 0, 0, 2, 3)
    assert roll.is_messy
    assert not roll.can_avoid_messy_critical

    roll = gen_roll(0, 0, 1, 0, 0, 0, 0, 3)
    assert not roll.is_messy
    assert not roll.can_avoid_messy_critical


def test_can_risky_avoid_messy():
    """Test the risky avoid messy options."""
    roll = gen_roll(1, 0, 1, 0, 0, 0, 1, 3)
    assert roll.is_messy
    assert roll.can_avoid_messy_critical
    assert roll.can_risky_messy_critical

    roll = gen_roll(0, 0, 1, 0, 0, 0, 1, 3)
    assert roll.is_messy
    assert roll.can_avoid_messy_critical
    assert not roll.can_risky_messy_critical


# DiceThrow tests


@pytest.mark.parametrize(
    "dice,expected_count",
    [
        ([1, 5, 6, 8, 10], 5),
        ([], 0),
        ([10], 1),
        ([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 10),
    ],
)
def test_dicethrow_count(dice, expected_count):
    """Test that count returns the number of dice."""
    throw = DiceThrow(dice)
    assert throw.count == expected_count


@pytest.mark.parametrize(
    "dice,expected_ones",
    [
        ([1, 1, 5, 6, 10], 2),
        ([2, 3, 4, 5, 6], 0),
        ([1, 1, 1], 3),
        ([1], 1),
        ([], 0),
    ],
)
def test_dicethrow_ones(dice, expected_ones):
    """Test counting ones in the dice."""
    throw = DiceThrow(dice)
    assert throw.ones == expected_ones


@pytest.mark.parametrize(
    "dice,expected_tens",
    [
        ([10, 10, 5, 6, 1], 2),
        ([1, 2, 3, 4, 5], 0),
        ([10, 10, 10, 10], 4),
        ([10], 1),
        ([], 0),
    ],
)
def test_dicethrow_tens(dice, expected_tens):
    """Test counting tens in the dice."""
    throw = DiceThrow(dice)
    assert throw.tens == expected_tens


@pytest.mark.parametrize(
    "dice,expected_failures",
    [
        ([1, 2, 3, 4, 5, 6, 10], 5),  # 1-5 are failures
        ([6, 7, 8, 9, 10], 0),
        ([1, 5], 2),
        ([1, 2, 3, 4, 5], 5),
        ([], 0),
    ],
)
def test_dicethrow_failures(dice, expected_failures):
    """Test counting failures (1-5)."""
    throw = DiceThrow(dice)
    assert throw.failures == expected_failures


@pytest.mark.parametrize(
    "dice,expected_successes",
    [
        ([1, 5, 6, 8, 10], 3),  # 6, 8, 10 are successes
        ([1, 2, 3, 4, 5], 0),
        ([6, 7, 8, 9, 10], 5),
        ([6], 1),
        ([], 0),
    ],
)
def test_dicethrow_successes(dice, expected_successes):
    """Test counting successes (6-10)."""
    throw = DiceThrow(dice)
    assert throw.successes == expected_successes


def test_dicethrow_edge_cases():
    """Test edge cases with all tens and all ones."""
    # All tens
    throw = DiceThrow([10, 10, 10])
    assert throw.count == 3
    assert throw.tens == 3
    assert throw.successes == 3
    assert throw.failures == 0
    assert throw.ones == 0

    # All ones
    throw = DiceThrow([1, 1, 1])
    assert throw.count == 3
    assert throw.ones == 3
    assert throw.failures == 3
    assert throw.successes == 0
    assert throw.tens == 0
