"""Tests for inconnu/misc/changelog.py's text formatting."""

import pytest

from inconnu.misc.changelog import compact_text, split_sections


@pytest.mark.parametrize(
    "text,expected",
    [
        ("## Fixes\n\n- A fix", "## Fixes\n- A fix"),
        ("- A fix\n\n## Features", "- A fix\n## Features"),
        ("# v1.0\n\n## Fixes\n\n- A fix", "# v1.0\n## Fixes\n- A fix"),
        ("- One\n\n### Sub\n\n- Two", "- One\n### Sub\n- Two"),
        ("First paragraph\n\nSecond paragraph", "First paragraph\n\nSecond paragraph"),
        ("#hashtag\n\ntext", "#hashtag\n\ntext"),
        ("- A fix\n\n\n## Features\n\n\n- A feature", "- A fix\n## Features\n- A feature"),
        ("## Fixes\r\n\r\n- A fix\r\n\r\n## Features", "## Fixes\n- A fix\n## Features"),
        ("One\r\n\r\nTwo", "One\n\nTwo"),
        ("No headings here", "No headings here"),
        ("", ""),
    ],
)
def test_compact_text(text: str, expected: str):
    """Blank lines around headings are removed; others are kept."""
    assert compact_text(text) == expected


def test_split_sections():
    """Each "##" heading starts a new, compacted section."""
    text = "## Fixes\n\n- A fix\n\n## Features\n\n- A feature\n\nMore detail"

    assert split_sections(text) == [
        "## Fixes\n- A fix",
        "## Features\n- A feature\n\nMore detail",
    ]


def test_split_sections_crlf():
    """Windows line endings split like Unix ones."""
    text = "## Fixes\r\n\r\n- A fix\r\n\r\n## Features\r\n- A feature"
    assert split_sections(text) == ["## Fixes\n- A fix", "## Features\n- A feature"]


def test_split_sections_preamble():
    """Text before the first "##" heading is its own section."""
    text = "Summary\n\n## Fixes\n- A fix"
    assert split_sections(text) == ["Summary", "## Fixes\n- A fix"]


def test_split_sections_other_headings():
    """Only "##" headings split; "#" and "###" stay in their section."""
    text = "# v1.0\n## Fixes\n### Dice\n- A fix\n#### Detail"

    assert split_sections(text) == ["# v1.0", "## Fixes\n### Dice\n- A fix\n#### Detail"]


def test_split_sections_no_headings():
    """Text without headings is a single section."""
    assert split_sections("- A fix\n\n- Another") == ["- A fix\n\n- Another"]
