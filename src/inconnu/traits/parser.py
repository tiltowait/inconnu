"""traits/parser.py - Parses trait-based arguments."""

import re

from constants import MAX_TRAIT_RATING, name_key
from inconnu.traits import traitcommon
from utils.text import straighten_apostrophes

DELIMITER = ";"


def split_traits(syntax: str) -> list[str]:
    """Split semicolon-delimited input into its items, collapsing whitespace,
    straightening curly apostrophes, and dropping empty items."""
    syntax = straighten_apostrophes(syntax)
    items = (" ".join(item.split()) for item in syntax.split(DELIMITER))
    return [item for item in items if item]


def parse_traits(syntax: str, *, disciplines: bool) -> dict[str, int | None]:
    """Parse semicolon-delimited "trait=rating" input into a dictionary. The
    rating is optional, and "trait rating" works, too."""
    ratings: dict[str, int | None] = {}
    seen: dict[str, str] = {}  # Name without case or spaces -> name as given

    for item in split_traits(syntax):
        if re.search(r"\d\s*['A-Za-z_]", item):
            # A word after a rating starts another trait
            raise SyntaxError(f"Separate traits with `{DELIMITER}`. Invalid: `{item}`.")

        item = re.sub(r"\s*=\s*", "=", item)
        item = re.sub(r"(?<=[A-Za-z_']) (?=\d+$)", "=", item)  # "trait rating"
        trait, *values = item.split("=")

        traitcommon.validate_trait_names(trait, disciplines=disciplines)

        if len(values) > 1:
            raise SyntaxError(f"Invalid argument: `{item}`.")

        rating = None
        if values:
            if not values[0].isdigit():
                raise SyntaxError(f"`{trait}` must be a number between 0 and {MAX_TRAIT_RATING}.")

            rating = int(values[0])

            if not 0 <= rating <= MAX_TRAIT_RATING:
                raise ValueError(
                    f"`{trait}` must be between 0 and {MAX_TRAIT_RATING}. (Got {rating}.)"
                )

        # Lookups ignore case and, failing that, spaces, so these are the same
        key = name_key(trait)
        if (first := seen.get(key)) is not None:
            if first == trait:
                raise SyntaxError(f"You can only add `{trait}` once.")
            raise SyntaxError(f"`{first}` and `{trait}` are the same trait.")
        seen[key] = trait

        ratings[trait] = rating

    return ratings
