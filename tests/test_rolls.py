"""Test basic roll logic."""

import unittest

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


class TestRollOutcomes(unittest.TestCase):
    """
    This suite tests the following roll outcome stats:

      * Total successes
      * Margin
      * Outcome string
      * Computed boolean equalities (is_messy, is_successful, etc.)

    It tests all six types of outcomes, including both types of messy critical.
    """

    def test_bestial_failure(self):
        """This roll should be a bestial failure."""
        roll = gen_roll(1, 2, 1, 1, 1, 1, 0, 5)

        self.assertTrue(roll.is_bestial)
        self.assertEqual(roll.outcome, "bestial")
        self.assertEqual(roll.total_successes, 4)
        self.assertEqual(roll.margin, -1)

        self.assertFalse(roll.is_total_failure)
        self.assertFalse(roll.is_failure)
        self.assertFalse(roll.is_successful)
        self.assertFalse(roll.is_critical)
        self.assertFalse(roll.is_messy)

    def test_total_failure(self):
        """This roll should be a total failure."""
        roll = gen_roll(1, 0, 0, 0, 0, 0, 0, 2)

        self.assertTrue(roll.is_total_failure)
        self.assertFalse(roll.is_failure)
        self.assertEqual(roll.outcome, "total_fail")
        self.assertEqual(roll.total_successes, 0)
        self.assertEqual(roll.margin, -2)

        self.assertFalse(roll.is_bestial)
        self.assertFalse(roll.is_successful)
        self.assertFalse(roll.is_messy)
        self.assertFalse(roll.is_critical)

    def test_failure(self):
        """This roll should be a simple failure."""
        roll = gen_roll(0, 1, 0, 0, 0, 0, 0, 2)

        self.assertTrue(roll.is_failure)
        self.assertEqual(roll.outcome, "fail")
        self.assertEqual(roll.total_successes, 1)
        self.assertEqual(roll.margin, -1)

        self.assertFalse(roll.is_total_failure)
        self.assertFalse(roll.is_bestial)
        self.assertFalse(roll.is_successful)
        self.assertFalse(roll.is_messy)
        self.assertFalse(roll.is_critical)

    def test_success(self):
        """This roll should be a plain success."""
        roll = gen_roll(0, 2, 1, 0, 0, 0, 0, 3)

        self.assertTrue(roll.is_successful)
        self.assertEqual(roll.outcome, "success")
        self.assertEqual(roll.total_successes, 3)
        self.assertEqual(roll.margin, 0)

        self.assertFalse(roll.is_bestial)
        self.assertFalse(roll.is_total_failure)
        self.assertFalse(roll.is_failure)
        self.assertFalse(roll.is_messy)
        self.assertFalse(roll.is_critical)

    def test_messy_critical(self):
        """This roll should be a messy critical."""
        roll = gen_roll(0, 0, 0, 1, 0, 0, 2, 3)

        self.assertTrue(roll.is_successful)
        self.assertTrue(roll.is_messy)
        self.assertEqual(roll.outcome, "messy")
        self.assertEqual(roll.total_successes, 4)
        self.assertEqual(roll.margin, 1)

        self.assertFalse(roll.is_bestial)
        self.assertFalse(roll.is_total_failure)
        self.assertFalse(roll.is_failure)
        self.assertFalse(roll.is_critical)

        # A messy critical is still messy if there are two normal 10s
        roll = gen_roll(0, 0, 4, 1, 0, 0, 1, 3)
        self.assertTrue(roll.is_messy)
        self.assertEqual(roll.total_successes, 9)
        self.assertEqual(roll.margin, 6)

    def test_critical(self):
        """This roll should be a critical success."""
        roll = gen_roll(0, 1, 3, 0, 0, 0, 0, 3)

        self.assertTrue(roll.is_successful)
        self.assertTrue(roll.is_critical)
        self.assertEqual(roll.outcome, "critical")
        self.assertEqual(roll.total_successes, 6)
        self.assertEqual(roll.margin, 3)

        self.assertFalse(roll.is_bestial)
        self.assertFalse(roll.is_total_failure)
        self.assertFalse(roll.is_failure)
        self.assertFalse(roll.is_messy)


class TestRollOpportunities(unittest.TestCase):
    """
    This suite tests the different WP opportunities.

    There are an absurd number of possible permutations. Rather than attempting
    to test them all, we simply test the major categories, looking at both true
    and false states.
    """

    def test_can_reroll_failures(self):
        """Test the various reroll failure states."""
        roll = gen_roll(3, 0, 0, 0, 1, 1, 0, 3)
        self.assertTrue(roll.can_reroll_failures)

        roll = gen_roll(0, 3, 0, 0, 1, 1, 0, 3)
        self.assertFalse(roll.can_reroll_failures)

    def test_can_maximize_crits(self):
        """Test the maximize crits options."""
        roll = gen_roll(1, 1, 3, 0, 0, 0, 0, 3)
        self.assertTrue(roll.can_maximize_criticals)

        roll = gen_roll(0, 0, 3, 0, 0, 0, 0, 3)
        self.assertFalse(roll.can_maximize_criticals)

        roll = gen_roll(0, 0, 0, 0, 0, 0, 3, 3)
        self.assertFalse(roll.can_maximize_criticals)

    def test_can_avoid_messy(self):
        """Test the avoid messy options."""
        roll = gen_roll(0, 0, 1, 0, 0, 0, 1, 3)
        self.assertTrue(roll.is_messy)
        self.assertTrue(roll.can_avoid_messy_critical)

        roll = gen_roll(0, 0, 0, 0, 0, 0, 2, 3)
        self.assertTrue(roll.is_messy)
        self.assertFalse(roll.can_avoid_messy_critical)

        roll = gen_roll(0, 0, 1, 0, 0, 0, 0, 3)
        self.assertFalse(roll.is_messy)
        self.assertFalse(roll.can_avoid_messy_critical)

    def test_can_risky_avoid_messy(self):
        """Test the risky avoid messy options."""
        roll = gen_roll(1, 0, 1, 0, 0, 0, 1, 3)
        self.assertTrue(roll.is_messy)
        self.assertTrue(roll.can_avoid_messy_critical)
        self.assertTrue(roll.can_risky_messy_critical)

        roll = gen_roll(0, 0, 1, 0, 0, 0, 1, 3)
        self.assertTrue(roll.is_messy)
        self.assertTrue(roll.can_avoid_messy_critical)
        self.assertFalse(roll.can_risky_messy_critical)


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
