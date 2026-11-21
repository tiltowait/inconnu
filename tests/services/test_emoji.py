"""Tests for services/emoji.py."""

from unittest.mock import MagicMock

import discord
import pytest

from constants import Damage, Theme
from services.emoji import _EmojiManager

type MockAppEmoji = MagicMock

ZWSP = "\u200b"


def app_emoji(name: str) -> MockAppEmoji:
    """A mock app emoji that renders as its name."""
    emoji = MagicMock(spec=discord.AppEmoji)
    emoji.configure_mock(**{"name": name, "__str__.return_value": f":{name}:"})
    return emoji


@pytest.fixture
def manager() -> _EmojiManager:
    """An emoji manager with standard and themed emoji loaded."""
    mgr = _EmojiManager()
    names = ["ln_succ", "peach_ln_succ", "sup_dmg", "bruised_sup_dmg"]
    mgr._emojis = {name: app_emoji(name) for name in names}
    return mgr


@pytest.mark.parametrize(
    "theme,name,expected",
    [
        (Theme.STANDARD, "ln_succ", ":ln_succ:"),
        (Theme.CITRUS_SHERBERT, "ln_succ", ":peach_ln_succ:"),
        (Theme.STANDARD, Damage.SUPERFICIAL, ":sup_dmg:"),
        (Theme.BRUISED, Damage.SUPERFICIAL, ":bruised_sup_dmg:"),
    ],
)
def test_emoji_theme_prefix(manager: _EmojiManager, theme: Theme, name: str, expected: str):
    """Themes prefix the emoji name, after damage symbols are mapped. The
    standard theme has no prefix."""
    assert manager.emoji(theme, name) == expected + ZWSP


def test_get_uses_theme(manager: _EmojiManager):
    """get() returns copies of the themed emoji."""
    assert manager.get(Theme.CITRUS_SHERBERT, "ln_succ", 3) == [":peach_ln_succ:" + ZWSP] * 3


def test_unicode_emoji_ignore_theme(manager: _EmojiManager):
    """Unicode emoji have no themed versions."""
    assert manager.emoji(Theme.BRUISED, "bp_filled").startswith(":red_circle:")


def test_missing_themed_emoji_falls_back(manager: _EmojiManager):
    """A theme without the emoji falls back to the standard one."""
    assert manager.emoji(Theme.BRUISED, "ln_succ") == ":ln_succ:" + ZWSP


def test_missing_emoji_raises(manager: _EmojiManager):
    """An emoji missing from every theme is an error."""
    with pytest.raises(KeyError):
        manager.emoji(Theme.BRUISED, "ln_crit")
