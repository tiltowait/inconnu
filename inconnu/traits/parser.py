"""traits/parser.py - Parses trait-based arguments."""

from . import traitcommon

def parse_traits(*args) -> dict:
    """Parses arguments and puts them into a dictionary."""
    ratings = {}

    for arg in args:
        split = arg.split("=")
        trait = split[0].strip()
        rating = None

        if traitcommon.VALID_TRAIT_PATTERN.match(trait) is None:
            raise SyntaxError(f"Invalid trait name: `{trait}`.")

        if len(split) > 2:
            raise SyntaxError(f"Invalid argument: `{arg}`.")

        if len(split) == 2:
            rating = split[1].strip()
            if not rating.isdigit():
                raise SyntaxError(f"`{trait}` must be a number between 0 and 5.")

            rating = int(split[1])

            if not 0 <= rating <= 5:
                raise ValueError(f"`{trait}` must be between 0 and 5. (Got {rating}.)")

        if trait in ratings:
            raise SyntaxError(f"You can only add `{trait}` once.")

        ratings[trait] = rating

    return ratings
