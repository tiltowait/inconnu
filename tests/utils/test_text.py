"""Tests for utils.text module."""

import pytest

from utils.text import (
    clean_text,
    contains_digit,
    de_camel,
    diff,
    fence,
    format_join,
    oxford_list,
    paginate,
    pluralize,
    pull_mentions,
)


@pytest.mark.parametrize(
    "text,de_underscore,expected",
    [
        ("CamelCase", False, "Camel Case"),
        ("Camel_Case", True, "Camel Case"),
        ("Camel_Case", False, "Camel_Case"),
        ("TheCamel_Case", False, "The Camel_Case"),
        ("TheCamel_Case", True, "The Camel Case"),
        ("dB", True, "d B"),
    ],
)
def test_de_camel(text: str, de_underscore: bool, expected: str):
    assert de_camel(text, de_underscore) == expected


@pytest.mark.parametrize(
    "value,noun,expected",
    [
        (1, "success", "1 success"),
        (2, "success", "2 successes"),
        (0, "success", "0 successes"),
        (1, "die", "1 die"),
        (5, "die", "5 dice"),
        (1, "specialty", "1 specialty"),
        (3, "specialty", "3 specialties"),
        (1, "vampire", "1 vampire"),
        (3, "vampire", "3 vampires"),
        (1, "Success", "1 Success"),
        (2, "Success", "2 Successes"),
        (2, "Die", "2 Dice"),
    ],
)
def test_pluralize(value: int, noun: str, expected: str):
    """Test pluralization of nouns."""
    assert pluralize(value, noun) == expected


@pytest.mark.parametrize(
    "string,expected",
    [
        ("hello", False),
        ("hello123", True),
        ("123", True),
        ("0", True),
        ("test9ing", True),
        ("", False),
        (None, False),
    ],
)
def test_contains_digit(string: str, expected: bool):
    """Test digit detection in strings."""
    assert contains_digit(string) == expected


def test_paginate_strings():
    """Test paginating strings."""
    # Simple case - everything fits in one page
    result = paginate(100, "short", "text")
    assert len(result) == 1
    assert "short" in result[0]
    assert "text" in result[0]

    # Multiple pages needed
    long_text = "a" * 150
    result = paginate(100, "header", long_text, "footer")
    assert len(result) > 1


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello    world", "hello world"),
        ("  extra   spaces  ", "extra spaces"),
        ("single", "single"),
        ("  leading", "leading"),
        ("trailing  ", "trailing"),
        ("multiple   gaps   here", "multiple gaps here"),
    ],
)
def test_clean_text(text: str, expected: str):
    """Test removing extra spaces from text."""
    assert clean_text(text) == expected


@pytest.mark.parametrize(
    "seq,conjunction,expected",
    [
        (["a"], "and", "a"),
        (["a", "b"], "and", "a and b"),
        (["a", "b", "c"], "and", "a, b, and c"),
        (["x", "y", "z", "w"], "and", "x, y, z, and w"),
        (["a", "b"], "or", "a or b"),
        (["a", "b", "c"], "or", "a, b, or c"),
        ([1, 2, 3], "and", "1, 2, and 3"),
    ],
)
def test_oxford_list(seq, conjunction: str, expected: str):
    """Test Oxford comma formatting."""
    assert oxford_list(seq, conjunction) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Hey <@123>!", {"<@123>"}),
        ("Hey <@123> and <@456>!", {"<@123>", "<@456>"}),
        ("Role <@&789>", {"<@&789>"}),
        ("Channel <#999>", {"<#999>"}),
        ("<@111> <@&222> <#333>", {"<@111>", "<@&222>", "<#333>"}),
        ("No mentions here", set()),
        ("", set()),
        ("<@123> <@123>", {"<@123>"}),  # Duplicates removed
    ],
)
def test_pull_mentions(text: str, expected: set):
    """Test extracting Discord mentions from text."""
    assert pull_mentions(text) == expected


@pytest.mark.parametrize(
    "collection,separator,f,alt,expected",
    [
        (["a", "b", "c"], ", ", "`", "", "`a`, `b`, `c`"),
        (["x"], "-", "*", "", "*x*"),
        ([], ", ", "`", "None", "None"),
        (["foo", "bar"], " | ", "**", "", "**foo** | **bar**"),
    ],
)
def test_format_join(collection, separator: str, f: str, alt: str, expected: str):
    """Test formatting and joining collections."""
    assert format_join(collection, separator, f, alt) == expected


# New tests for diff function


def test_diff_basic_joined():
    """Test basic diff with joined output."""
    old = "Hello world"
    new = "Hello there"
    result = diff(old, new, join=True)
    assert isinstance(result, str)
    assert "- Hello world\n" in result
    assert "+ Hello there\n" in result


def test_diff_basic_list():
    """Test basic diff with list output."""
    old = "Hello world"
    new = "Hello there"
    result = diff(old, new, join=False)
    assert isinstance(result, list)
    assert any("- Hello world" in line for line in result)
    assert any("+ Hello there" in line for line in result)


def test_diff_multiline():
    """Test diff with multiline strings."""
    old = "Line 1\nLine 2\nLine 3"
    new = "Line 1\nModified Line 2\nLine 3"
    result = diff(old, new, join=True)
    assert "  Line 1\n" in result
    assert "- Line 2\n" in result
    assert "+ Modified Line 2\n" in result
    assert "  Line 3\n" in result


def test_diff_no_pos_markers_false():
    """Test diff with position markers enabled."""
    old = "Hello"
    new = "Hallo"
    result = diff(old, new, join=False, no_pos_markers=False)
    # With position markers enabled, should have '?' lines
    has_question_mark = any(line.startswith("?") for line in result)
    assert has_question_mark


def test_diff_strip():
    """Test diff with strip option."""
    old = "Hello"
    new = "World"
    result = diff(old, new, join=False, strip=True)
    # All lines should be stripped
    assert all(line == line.strip() for line in result)


def test_diff_identical():
    """Test diff with identical strings."""
    text = "Same text"
    result = diff(text, text, join=True)
    assert "  Same text\n" in result
    assert "-" not in result
    assert "+" not in result


def test_diff_empty_strings():
    """Test diff with empty strings."""
    result = diff("", "content", join=True)
    assert "+ content\n" in result

    result = diff("content", "", join=True)
    assert "- content\n" in result


# New tests for fence function


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("hello", "`hello`"),
        ("", "``"),
        ("test code", "`test code`"),
        ("123", "`123`"),
        ("special!@#", "`special!@#`"),
    ],
)
def test_fence(input_str: str, expected: str):
    """Test adding code fence around strings."""
    assert fence(input_str) == expected


def test_fence_preserves_content():
    """Test that fence doesn't modify the content."""
    original = "test string with spaces"
    fenced = fence(original)
    assert fenced == f"`{original}`"
    assert original in fenced
