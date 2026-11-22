"""Tests for inconnu/character/display/trackmoji.py"""

from collections.abc import Iterator
from unittest.mock import patch

import pytest

from constants import Theme
from inconnu.character.display.trackmoji import emojify_humanity, emojify_hunger, emojify_track


class _MockEmojis:
    """Predictable stand-in for services.emojis."""

    def emoji(self, theme: Theme, key: str) -> str:
        """The emoji's placeholder: ":hunger:", or ":bruised_hunger:" in a theme."""
        return f":{theme}_{key}:" if theme else f":{key}:"

    def get(self, theme: Theme, key: str, count=1) -> list[str]:
        """'count' copies of the emoji's placeholder."""
        return [self.emoji(theme, key)] * count


@pytest.fixture
def mock_emojis() -> Iterator[None]:
    """Patch services.emojis with a predictable mock."""
    with patch("services.emojis", _MockEmojis()):
        yield


# emojify_humanity


def test_humanity_normal_no_overlap(mock_emojis: None):
    """No overlap: filled=7, unfilled=1, stains=2."""
    result = emojify_humanity(Theme.STANDARD, 7, 2)
    assert result.count(":hu_filled:") == 7
    assert result.count(":hu_unfilled:") == 1
    assert result.count(":stain:") == 2
    assert result.count(":degen:") == 0


def test_humanity_overlap(mock_emojis: None):
    """Stains exceed available unfilled boxes: humanity=8, stains=4 → overlapped=2."""
    # unfilled = 10-8-4 = -2 → overlapped=2, stains=2, unfilled=0, filled=6
    result = emojify_humanity(Theme.STANDARD, 8, 4)
    assert result.count(":hu_filled:") == 6
    assert result.count(":degen:") == 2
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 2


def test_humanity_full_no_stains(mock_emojis: None):
    """Max humanity, no stains: all 10 boxes filled."""
    result = emojify_humanity(Theme.STANDARD, 10, 0)
    assert result.count(":hu_filled:") == 10
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 0
    assert result.count(":degen:") == 0


def test_humanity_zero_no_stains(mock_emojis: None):
    """Zero humanity, no stains: all 10 boxes unfilled."""
    result = emojify_humanity(Theme.STANDARD, 0, 0)
    assert result.count(":hu_filled:") == 0
    assert result.count(":hu_unfilled:") == 10
    assert result.count(":stain:") == 0
    assert result.count(":degen:") == 0


def test_humanity_zero_max_stains(mock_emojis: None):
    """Zero humanity, 10 stains: unfilled=0, no overlap triggered."""
    # unfilled = 10-0-10 = 0, so overlapped path is not taken
    result = emojify_humanity(Theme.STANDARD, 0, 10)
    assert result.count(":hu_filled:") == 0
    assert result.count(":degen:") == 0
    assert result.count(":hu_unfilled:") == 0
    assert result.count(":stain:") == 10


def test_humanity_total_always_ten(mock_emojis: None):
    """Emoji total is always 10 across all valid humanity/stain combinations."""
    for humanity in range(11):
        for stains in range(11):
            result = emojify_humanity(Theme.STANDARD, humanity, stains)
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
def test_emojify_track_gap_count(length: int, expected_gaps: int, mock_emojis: None):
    """Separator dots are inserted at every 5-box boundary."""
    result = emojify_track(Theme.STANDARD, "x" * length)
    assert result.count("∙") == expected_gaps


# emojify_hunger


@pytest.mark.parametrize("level", range(6))
def test_emojify_hunger_total_always_five(level: int, mock_emojis: None):
    """Filled + unfilled hunger boxes always totals 5."""
    result = emojify_hunger(Theme.STANDARD, level)
    assert result.count(":hunger:") + result.count(":no_hunger:") == 5


@pytest.mark.parametrize("level", range(6))
def test_emojify_hunger_filled_matches_level(level: int, mock_emojis: None):
    """Filled hunger count matches the hunger level exactly."""
    result = emojify_hunger(Theme.STANDARD, level)
    assert result.count(":hunger:") == level


# Themes


def test_trackers_use_theme(mock_emojis: None):
    """Every tracker draws its emoji in the given theme."""
    assert emojify_track(Theme.BRUISED, "/") == ":bruised_/:"
    assert emojify_hunger(Theme.BRUISED, 5).count(":bruised_hunger:") == 5
    assert emojify_humanity(Theme.BRUISED, 10, 0).count(":bruised_hu_filled:") == 10
