"""Tests for inconnu/character/display/trackmoji.py"""

from unittest.mock import patch

import pytest

from inconnu.character.display.trackmoji import emojify_humanity, emojify_hunger, emojify_track


class _MockEmojis:
    """Predictable stand-in for services.emojis."""

    def __getitem__(self, key: str) -> str:
        return f":{key}:"

    def get(self, key: str, count: int = 1) -> list[str]:
        return [f":{key}:"] * count


@pytest.fixture
def mock_emojis():
    """Patch services.emojis with a predictable mock."""
    with patch("services.emojis", _MockEmojis()):
        yield


# emojify_humanity


def test_humanity_normal_no_overlap(mock_emojis):
    """No overlap: filled=7, unfilled=1, stains=2."""
    result = emojify_humanity(7, 2)
    assert result.count(":hu_filled:") == 7
    assert result.count(":hu_unfilled:") == 1
    assert result.count(":stain:") == 2
    assert result.count(":degen:") == 0


def test_humanity_overlap(mock_emojis):
    """Stains exceed available unfilled boxes: humanity=8, stains=4 → overlapped=2."""
    # unfilled = 10-8-4 = -2 → overlapped=2, stains=2, unfilled=0, filled=6
    result = emojify_humanity(8, 4)
    assert result.count(":hu_filled:") == 6
    assert result.count(":degen:") == 2
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 2


def test_humanity_full_no_stains(mock_emojis):
    """Max humanity, no stains: all 10 boxes filled."""
    result = emojify_humanity(10, 0)
    assert result.count(":hu_filled:") == 10
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 0
    assert result.count(":degen:") == 0


def test_humanity_zero_no_stains(mock_emojis):
    """Zero humanity, no stains: all 10 boxes unfilled."""
    result = emojify_humanity(0, 0)
    assert result.count(":hu_filled:") == 0
    assert result.count(":hu_unfilled:") == 10
    assert result.count(":stain:") == 0
    assert result.count(":degen:") == 0


def test_humanity_zero_max_stains(mock_emojis):
    """Zero humanity, 10 stains: unfilled=0, no overlap triggered."""
    # unfilled = 10-0-10 = 0, so overlapped path is not taken
    result = emojify_humanity(0, 10)
    assert result.count(":hu_filled:") == 0
    assert result.count(":degen:") == 0
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 10


def test_humanity_total_always_ten(mock_emojis):
    """Emoji total is always 10 across all valid humanity/stain combinations."""
    for humanity in range(11):
        for stains in range(11):
            result = emojify_humanity(humanity, stains)
            total = (
                result.count(":hu_filled:")
                + result.count(":hu_unfilled:")
                + result.count(":stain:")
                + result.count(":degen:")
            )
            assert total == 10, f"humanity={humanity}, stains={stains} → {total} boxes"


# emojify_track gap insertion


@pytest.mark.parametrize(
    "length, expected_gaps",
    [
        (5, 0),
        (6, 1),
        (10, 1),
        (11, 2),
    ],
)
def test_emojify_track_gap_count(length, expected_gaps, mock_emojis):
    """Separator dots are inserted at every 5-box boundary."""
    result = emojify_track("x" * length)
    assert result.count("∙") == expected_gaps


# emojify_hunger


@pytest.mark.parametrize("level", range(6))
def test_emojify_hunger_total_always_five(level, mock_emojis):
    """Filled + unfilled hunger boxes always totals 5."""
    result = emojify_hunger(level)
    assert result.count(":hunger:") + result.count(":no_hunger:") == 5


@pytest.mark.parametrize("level", range(6))
def test_emojify_hunger_filled_matches_level(level, mock_emojis):
    """Filled hunger count matches the hunger level exactly."""
    result = emojify_hunger(level)
    assert result.count(":hunger:") == level
