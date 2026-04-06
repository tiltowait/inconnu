"""Tests for inconnu.header (header_title, blush_text)."""

from unittest.mock import MagicMock

from inconnu.header import blush_text, header_title

# --- header_title ---


def test_single_field():
    assert header_title("Nadea") == "Nadea"


def test_two_fields():
    assert header_title("Nadea", "The Elysium") == "Nadea • The Elysium"


def test_three_fields():
    assert header_title("Nadea", "The Elysium", "Blushed") == "Nadea • The Elysium • Blushed"


def test_none_filtered():
    assert header_title("Nadea", None, "Blushed") == "Nadea • Blushed"


def test_all_none():
    assert header_title(None, None, None) == ""


def test_no_fields():
    assert header_title() == ""


def test_none_at_edges():
    assert header_title(None, "Nadea", None) == "Nadea"


# --- blush_text ---


def _make_character(*, is_vampire: bool) -> MagicMock:
    char = MagicMock()
    char.is_vampire = is_vampire
    return char


def test_blush_active():
    assert blush_text(_make_character(is_vampire=True), blush=1) == "Blushed"


def test_blush_inactive():
    assert blush_text(_make_character(is_vampire=True), blush=0) == "Not Blushed"


def test_blush_na():
    assert blush_text(_make_character(is_vampire=True), blush=-1) is None


def test_blush_mortal():
    assert blush_text(_make_character(is_vampire=False), blush=1) is None
