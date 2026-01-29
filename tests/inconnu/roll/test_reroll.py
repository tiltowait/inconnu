"""Tests for inconnu/roll/roll.py reroll strategy functions."""

from unittest.mock import patch


from inconnu.roll.roll import (
    _avoid_messy,
    _maximize_criticals,
    _reroll_failures,
    _risky_avoid_messy,
)


# Test _reroll_failures


def test_reroll_failures_all_successes():
    """Test that successes are not rerolled."""
    dice = [6, 7, 8, 9, 10]
    result = _reroll_failures(dice)
    assert result == dice  # All successes, nothing rerolled


def test_reroll_failures_all_failures():
    """Test rerolling up to 3 failures."""
    dice = [1, 2, 3, 4, 5]
    with patch("inconnu.d10", side_effect=[7, 8, 9]):
        result = _reroll_failures(dice)

    # First 3 failures rerolled, last 2 kept
    assert result == [7, 8, 9, 4, 5]


def test_reroll_failures_max_three():
    """Test that at most 3 dice are rerolled."""
    dice = [1, 2, 3, 4, 5]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _reroll_failures(dice)

    # Only first 3 rerolled
    assert result == [10, 10, 10, 4, 5]


def test_reroll_failures_mixed():
    """Test rerolling failures in mixed pool."""
    dice = [2, 6, 3, 8, 1]
    with patch("inconnu.d10", side_effect=[9, 7, 6]):
        result = _reroll_failures(dice)

    # Rerolls: 2->9, 3->7, 1->6
    assert result == [9, 6, 7, 8, 6]


def test_reroll_failures_exactly_three_failures():
    """Test rerolling exactly 3 failures."""
    dice = [1, 2, 3, 6, 7]
    with patch("inconnu.d10", side_effect=[8, 9, 10]):
        result = _reroll_failures(dice)

    assert result == [8, 9, 10, 6, 7]


def test_reroll_failures_one_failure():
    """Test rerolling single failure."""
    dice = [5, 6, 7, 8]
    with patch("inconnu.d10", return_value=10):
        result = _reroll_failures(dice)

    assert result == [10, 6, 7, 8]


# Test _maximize_criticals


def test_maximize_criticals_all_criticals():
    """Test that all criticals are kept."""
    dice = [10, 10, 10]
    result = _maximize_criticals(dice)
    assert result == [10, 10, 10]


def test_maximize_criticals_no_criticals_all_failures():
    """Test rerolling failures when no criticals present."""
    dice = [1, 2, 3, 4, 5]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _maximize_criticals(dice)

    # First 3 failures rerolled
    assert result == [10, 10, 10, 4, 5]


def test_maximize_criticals_converts_successes_to_failures():
    """Test that non-critical successes are converted to failures for rerolling."""
    dice = [10, 6, 7, 8, 9]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _maximize_criticals(dice)

    # 6, 7, 8 converted to 1 (failures), then rerolled to 10s
    # Original: [10, 6, 7, 8, 9]
    # After conversion: [10, 1, 1, 1, 9]
    # After reroll: [10, 10, 10, 10, 9]
    assert result == [10, 10, 10, 10, 9]


def test_maximize_criticals_mixed_pool():
    """Test maximize criticals with mixed results."""
    dice = [10, 10, 3, 7, 2]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _maximize_criticals(dice)

    # Has 2 failures (3, 2) and 1 non-crit success (7)
    # Converts 7 to 1 to reach 3 failures
    # Rerolls all 3 failures
    assert result == [10, 10, 10, 10, 10]


def test_maximize_criticals_enough_failures():
    """Test when there are already 3+ failures (no conversion needed)."""
    dice = [10, 1, 2, 3, 4]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _maximize_criticals(dice)

    # Already has 4 failures, rerolls first 3
    assert result == [10, 10, 10, 10, 4]


def test_maximize_criticals_two_failures_one_success():
    """Test converting one success when only 2 failures exist."""
    dice = [10, 2, 3, 6]
    with patch("inconnu.d10", side_effect=[10, 10, 10]):
        result = _maximize_criticals(dice)

    # 2 failures + convert 6 to 1 = 3 failures
    # Then reroll all 3
    assert result == [10, 10, 10, 10]


# Test _avoid_messy


def test_avoid_messy_no_criticals():
    """Test that non-criticals are not rerolled."""
    dice = [1, 5, 6, 8, 9]
    result = _avoid_messy(dice)
    assert result == dice


def test_avoid_messy_all_criticals():
    """Test rerolling up to 3 criticals."""
    dice = [10, 10, 10, 10]
    with patch("inconnu.d10", side_effect=[5, 6, 7]):
        result = _avoid_messy(dice)

    # First 3 criticals rerolled
    assert result == [5, 6, 7, 10]


def test_avoid_messy_exactly_three_criticals():
    """Test rerolling exactly 3 criticals."""
    dice = [10, 10, 10, 6, 7]
    with patch("inconnu.d10", side_effect=[1, 2, 3]):
        result = _avoid_messy(dice)

    assert result == [1, 2, 3, 6, 7]


def test_avoid_messy_one_critical():
    """Test rerolling single critical."""
    dice = [5, 6, 7, 10]
    with patch("inconnu.d10", return_value=8):
        result = _avoid_messy(dice)

    assert result == [5, 6, 7, 8]


def test_avoid_messy_mixed_pool():
    """Test avoiding messy in mixed pool."""
    dice = [2, 10, 6, 10, 8]
    with patch("inconnu.d10", side_effect=[3, 4]):
        result = _avoid_messy(dice)

    # Rerolls both 10s
    assert result == [2, 3, 6, 4, 8]


# Test _risky_avoid_messy


def test_risky_avoid_messy_no_criticals():
    """Test risky with no criticals - rerolls up to 3 failures."""
    dice = [1, 2, 3, 6, 7]
    with patch("inconnu.d10", side_effect=[8, 9, 10]):
        result = _risky_avoid_messy(dice)

    # Rerolls 3 failures
    assert result == [8, 9, 10, 6, 7]


def test_risky_avoid_messy_all_criticals():
    """Test risky with all criticals - rerolls all of them."""
    dice = [10, 10, 10, 10]
    with patch("inconnu.d10", side_effect=[5, 6, 7, 8]):
        result = _risky_avoid_messy(dice)

    # Rerolls all 4 tens (no limit when only tens)
    assert result == [5, 6, 7, 8]


def test_risky_avoid_messy_one_critical_two_failures():
    """Test risky with 1 critical and 2 failures = 3 rerolls total."""
    dice = [10, 2, 3, 6, 7]
    with patch("inconnu.d10", side_effect=[8, 9, 10]):
        result = _risky_avoid_messy(dice)

    # Rerolls: 10, 2, 3
    assert result == [8, 9, 10, 6, 7]


def test_risky_avoid_messy_two_criticals_one_failure():
    """Test risky with 2 criticals and 1 failure = 3 rerolls total."""
    dice = [10, 10, 2, 6, 7]
    with patch("inconnu.d10", side_effect=[5, 5, 5]):
        result = _risky_avoid_messy(dice)

    # Rerolls: both 10s, then 1 failure (2)
    assert result == [5, 5, 5, 6, 7]


def test_risky_avoid_messy_three_criticals_no_failures():
    """Test risky with 3+ criticals and no failures."""
    dice = [10, 10, 10, 6, 7]
    with patch("inconnu.d10", side_effect=[1, 2, 3]):
        result = _risky_avoid_messy(dice)

    # Only rerolls 3 tens, no failures to reroll
    assert result == [1, 2, 3, 6, 7]


def test_risky_avoid_messy_one_critical_many_failures():
    """Test risky with 1 critical and many failures - rerolls 3 total."""
    dice = [10, 1, 2, 3, 4]
    with patch("inconnu.d10", side_effect=[7, 8, 9]):
        result = _risky_avoid_messy(dice)

    # Rerolls: 10, then 2 failures (1, 2)
    # Leaves 3, 4 as-is
    assert result == [7, 8, 9, 3, 4]


def test_risky_avoid_messy_only_successes():
    """Test risky with only non-critical successes - nothing rerolled."""
    dice = [6, 7, 8, 9]
    result = _risky_avoid_messy(dice)
    assert result == dice


def test_risky_avoid_messy_exact_count():
    """Test that risky respects the 3 reroll limit exactly."""
    dice = [10, 10, 1, 2, 3, 4, 5]
    with patch("inconnu.d10", side_effect=[6, 7, 8]):
        result = _risky_avoid_messy(dice)

    # 2 tens + 1 failure = 3 rerolls
    assert result == [6, 7, 8, 2, 3, 4, 5]
