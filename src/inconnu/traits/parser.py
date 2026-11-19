"""traits/parser.py - Parses trait-based arguments."""

import re

from inconnu.traits import traitcommon

DELIMITER = ";"


def split_traits(syntax: str) -> list[str]:
    """Split semicolon-delimited input into its items, collapsing whitespace
    and dropping empty items."""
    items = (" ".join(item.split()) for item in syntax.split(DELIMITER))
    return [item for item in items if item]


def parse_traits(syntax: str, *, disciplines: bool) -> dict[str, int | None]:
    """Parse semicolon-delimited "trait=rating" input into a dictionary. The
    rating is optional, and "trait rating" works, too."""
    ratings: dict[str, int | None] = {}

    for item in split_traits(syntax):
        if re.search(r"\d\s*[A-Za-z_]", item):
            # A word after a rating starts another trait
            raise SyntaxError(f"Separate traits with `{DELIMITER}`. Invalid: `{item}`.")

        item = re.sub(r"\s*=\s*", "=", item)
        item = re.sub(r"(?<=[A-Za-z_]) (?=\d+$)", "=", item)  # "trait rating"
        trait, *values = item.split("=")

        traitcommon.validate_trait_names(trait, disciplines=disciplines)

        if len(values) > 1:
            raise SyntaxError(f"Invalid argument: `{item}`.")

        rating = None
        if values:
            if not values[0].isdigit():
                raise SyntaxError(f"`{trait}` must be a number between 0 and 5.")

            rating = int(values[0])

            if not 0 <= rating <= 5:
                raise ValueError(f"`{trait}` must be between 0 and 5. (Got {rating}.)")

        if trait in ratings:
            raise SyntaxError(f"You can only add `{trait}` once.")

        ratings[trait] = rating

    return ratings
