"""Miscellaneous tests."""

import random
import string
from math import ceil

import pytest

from inconnu.utils import de_camel, re_paginate


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


def test_re_paginate_simple():
    pages = re_paginate(["one", "two", "three"])
    assert pages == ["one\n\ntwo\n\nthree"]


def test_re_paginate_on_spaces():
    pages = []
    total = 0

    for _ in range(5):
        page = ""
        while len(page) < 3000:
            page += " " + generate_random_word(random.randint(1, 10))
        pages.append(page[1:])
        total += len(page)

    pages = re_paginate(pages)
    assert all(len(page) <= 2000 for page in pages)
    assert len(pages) == ceil(total / 2000)
    assert len("".join(pages)) == total - len(pages) / 2


def test_re_paginate_fallback():
    pages = []
    page_len = 3000
    total = 0

    for _ in range(5):
        pages.append("a" * page_len)
        total += page_len

    pages = re_paginate(pages)
    assert all(len(page) <= 2000 for page in pages)
    assert len(pages) == ceil(total / 2000)
    assert len("".join(pages)) == total


def test_re_paginate_preserves_newlines():
    """Ensure re_paginate() preserves newline counts."""
    text = "one\ntwo\n\nthree\nfour"
    pages = re_paginate([text])

    assert pages[0] == text


def generate_random_word(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))
