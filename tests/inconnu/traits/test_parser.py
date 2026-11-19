"""Tests for inconnu/traits/parser.py."""

import pytest

from inconnu.traits.parser import parse_traits, split_traits


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("", []),
        ("  ;  ; ", []),
        ("foo", ["foo"]),
        ("  foo   ", ["foo"]),
        ("foo bar", ["foo bar"]),
        ("foo   bar", ["foo bar"]),
        ("foo; bar; baz", ["foo", "bar", "baz"]),
        ("foo bar;baz;", ["foo bar", "baz"]),
        ("a=1;; b = 2", ["a=1", "b = 2"]),
    ],
)
def test_split_traits(syntax: str, expected: list[str]):
    """Semicolons separate items, whose whitespace is collapsed."""
    assert split_traits(syntax) == expected


@pytest.mark.parametrize(
    "syntax,expected",
    [
        ("t=2", {"t": 2}),
        (" t=2", {"t": 2}),
        ("t =   2 ", {"t": 2}),
        ("t 2", {"t": 2}),
        ("t", {"t": None}),
        ("t=2; u=3", {"t": 2, "u": 3}),
        ("Brawl=4;Academics=0;", {"Brawl": 4, "Academics": 0}),
        ("Animal Ken=3; Brawl=2 ", {"Animal Ken": 3, "Brawl": 2}),
        ("Animal   Ken 3; Big Cats", {"Animal Ken": 3, "Big Cats": None}),
        # Apostrophes, and curly ones from phones
        ("Beast's Fang=2; Dogs' 1", {"Beast's Fang": 2, "Dogs'": 1}),
        ("Beast\u2019s Fang=2; \u2018Til Death", {"Beast's Fang": 2, "'Til Death": None}),
    ],
)
def test_parse_traits(syntax: str, expected: dict[str, int | None]):
    """Items are "trait=rating", "trait rating", or a bare trait."""
    assert parse_traits(syntax, disciplines=False) == expected


@pytest.mark.parametrize(
    "syntax",
    ["a=1 b=2", "a 1 b 2", "Animal Ken=3 Brawl", "a=1 b=2; c=3", "a=1b", "a=1 'Til=2"],
)
def test_parse_traits_missing_semicolon(syntax: str):
    """A word after a rating means a missing semicolon."""
    with pytest.raises(SyntaxError, match="Separate traits with `;`"):
        parse_traits(syntax, disciplines=False)


@pytest.mark.parametrize(
    "syntax,error,match",
    [
        ("t==1", SyntaxError, "Invalid argument"),
        ("t=", SyntaxError, "must be a number"),
        ("t=x", SyntaxError, "must be a number"),
        ("t=6", ValueError, "must be between 0 and 5"),
        ("=1", SyntaxError, "letters, underscores, and apostrophes"),
        ("1=1", SyntaxError, "letters, underscores, and apostrophes"),
        ("t-x=1", SyntaxError, "letters, underscores, and apostrophes"),
        ("Ravenous Hunger=1", SyntaxError, "after its first word"),
        ("t=1; t=2", SyntaxError, "only add `t` once"),
    ],
)
def test_parse_traits_errors(syntax: str, error: type[Exception], match: str):
    """Invalid names, ratings, and duplicates are rejected."""
    with pytest.raises(error, match=match):
        parse_traits(syntax, disciplines=False)
