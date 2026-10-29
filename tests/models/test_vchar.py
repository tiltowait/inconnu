"""Tests for models/vchar.py."""

import pytest

from tests.characters import gen_char


@pytest.mark.parametrize("old_blush", [-1, 0])
def test_vampire_can_blush(old_blush: int):
    """A vampire can Blush even if their header was set to N/A at Humanity 9+."""
    vamp = gen_char("vampire")
    vamp.header.blush = old_blush
    vamp.set_blush(1)

    assert vamp.header.blush == 1


@pytest.mark.parametrize("splat", ["mortal", "ghoul", "thin-blood"])
def test_non_vampire_cannot_blush(splat: str):
    """Only full vampires Blush."""
    char = gen_char(splat)
    char.header.blush = -1
    char.set_blush(1)

    assert char.header.blush == -1
