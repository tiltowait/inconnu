"""String manipulation utilities."""

import re
from difflib import Differ
from typing import Any, Literal, overload


def clean_text(text: str) -> str:
    """Remove extra spaces in text."""
    return " ".join(text.split())


def de_camel(text: str, de_underscore=True) -> str:
    """CamelCase -> Camel Case. Also does underscores."""
    temp = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    if de_underscore:
        return temp.replace("_", " ")
    return temp


@overload
def diff(
    old: str, new: str, join: Literal[True] = True, no_pos_markers: bool = True, strip: bool = False
) -> str: ...


@overload
def diff(
    old: str, new: str, join: Literal[False], no_pos_markers: bool = True, strip: bool = False
) -> list[str]: ...


def diff(old: str, new: str, join=True, no_pos_markers=True, strip=False) -> list[str] | str:
    """Generate a diff between two strings."""

    def normalize(lines: list[str]) -> list[str]:
        """Normalize the lines to make more concise diffs."""
        if len(lines) == 1 and lines[0][-1] != "\n":
            lines[0] += "\n"
        return lines

    old_split = normalize(old.splitlines(True))
    new_split = normalize(new.splitlines(True))

    diff = Differ().compare(old_split, new_split)
    lines = [line + ("\n" if line[-1] != "\n" else "") for line in diff]

    if no_pos_markers:
        lines = [line for line in lines if line[0] != "?"]
    if strip:
        lines = [line.strip() for line in lines]
    if join:
        return "".join(lines)
    return lines


def format_join(collection: list, separator: str, f: str, alt="") -> str:
    """Join a collection by a separator, formatting each item."""
    return separator.join(map(lambda c: f"{f}{c}{f}", collection)) or alt


def pull_mentions(text: str) -> set[str]:
    """Pulls mentions from text."""
    mentions = re.findall(r"(<(?:@|@&|#)\d{1,30}>)", text)
    return set(mentions)


def oxford_list(seq: list[Any], conjunction="and") -> str:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    seq = [str(s) for s in seq]
    if len(seq) < 3:
        return f" {conjunction} ".join(seq)
    return ", ".join(seq[:-1]) + f", {conjunction} " + seq[-1]


def fence(string: str) -> str:
    """Add a code fence around a string."""
    return f"`{string}`"
