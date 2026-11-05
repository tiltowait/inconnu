"""Tests for inconnu.header (header_title)."""

from inconnu.header import header_title

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
