"""Miscellaneous tests."""

import random
import string
from datetime import datetime as dt
from math import ceil

import pytest

import inconnu
from inconnu.roleplay.search import convert_dates
from inconnu.utils import re_paginate
from inconnu.utils.text import (
    clean_text,
    contains_digit,
    de_camel,
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


def test_standard_re_paginate():
    """Tests re_paginate() on a long body of text."""
    with open("./tests/scrambled.txt", "r") as f:
        lines = f.readlines()
        text = "\n".join(lines)

    assert len(text) > 3000
    texts = [text, text, text]  # Just make it extra extra long

    pages = re_paginate(texts)
    words = [word for text in texts for word in text.split()]
    re_words = [word for page in pages for word in page.split()]

    assert words == re_words


def test_re_paginate_simple():
    """Ensure re_paginate() combines three small pages into one."""
    pages = re_paginate(["one", "two", "three"])
    assert pages == ["one\n\ntwo\n\nthree"]


def test_re_paginate_on_spaces():
    """Ensure re_paginate correctly splits pages on space."""
    words = []
    pages = []
    total = 0

    for _ in range(5):
        page = ""
        while len(page) < 3000:
            word = generate_random_word(random.randint(1, 10))
            page += " " + word
            words.append(word)
        pages.append(page[1:])
        total += len(page)

    pages = re_paginate(pages)
    assert all(len(page) <= 2000 for page in pages)
    assert len(pages) == ceil(total / 2000)
    assert len("".join(pages)) == total - len(pages) / 2

    # Check that the pages contain all the words in the same order
    rebuilt = [word for page in pages for word in page.split()]
    for w1, w2 in zip(words, rebuilt):
        assert w1 == w2, "Words don't all match"


def test_re_paginate_fallback():
    page_len = 3000
    pages = []
    full_str = ""

    for _ in range(5):
        word = "a" * page_len
        pages.append(word)
        full_str += word

    pages = re_paginate(pages)
    assert all(len(page) <= 2000 for page in pages)
    assert len(pages) == ceil(len(full_str) / 2000)
    assert "".join(pages) == full_str


def test_re_paginate_preserves_newlines():
    """Ensure re_paginate() preserves newline counts."""
    text = "one\ntwo\n\nthree\nfour"

    pages = re_paginate([text])
    assert pages[0] == text


def generate_random_word(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


@pytest.mark.asyncio
async def test_changelog():
    tag, changelog = await inconnu.misc.fetch_changelog()
    assert isinstance(tag, str)
    assert tag[0] == "v"
    assert isinstance(changelog, str)
    assert len(changelog) > 0


@pytest.mark.parametrize("res", ["Melancholy", "Choleric", "Phlegmatic", "Sanguine"])
def test_dyscrasias(res):
    dys = inconnu.reference.get_dyscrasia(res)
    assert dys is not None
    assert dys.name
    assert dys.description
    assert dys.page


@pytest.mark.parametrize(
    "after,before,exp_b,exp_a,error",
    [
        (None, None, None, None, False),
        (None, "20231110", None, dt(2023, 11, 10), False),
        ("20231010", None, dt(2023, 10, 10), None, False),
        ("20231010", "20231110", dt(2023, 10, 10), dt(2023, 11, 10), False),
        ("20231010", "20230910", None, None, ValueError),  # Date mismatch
        ("Bad date", "20231010", None, None, SyntaxError),
    ],
)
def test_convert_dates(after: str, before: str, exp_b: dt, exp_a: dt, error: Exception | None):
    if error:
        with pytest.raises(error):
            b, a = convert_dates(after, before)
    else:
        b, a = convert_dates(after, before)
        assert b == exp_b
        assert a == exp_a

        if before and after:
            assert before > after


# common.py utility tests


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


# Utils/__init__.py tests


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
