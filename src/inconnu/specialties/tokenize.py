"""Specialties input tokenizer."""

from inconnu.traits.parser import DELIMITER, split_traits
from utils.validation import validate_specialty_names, validate_trait_names

SYNTAX = f"```trait=spec, spec{DELIMITER} trait=spec```"


def tokenize(syntax: str) -> list[tuple[str, list[str]]]:
    """Tokenize semicolon-delimited "trait=spec, spec" input into (trait,
    specialties) pairs. Stray commas are ignored."""
    items = split_traits(syntax)
    if not items:
        raise SyntaxError("You must supply a trait and specialties.")

    matches = []
    for item in items:
        trait, *values = (part.strip() for part in item.split("="))
        if len(values) > 1:
            # A missing ; ("brawl=kindred occult=bahari", or a comma in its
            # place) and an extra = ("brawl=big cats=dogs") look alike, since
            # names have spaces, so the message covers both
            raise SyntaxError(
                f"Each trait takes one `=`, and traits are separated by `{DELIMITER}`. "
                f"Invalid: `{item}`."
            )
        if not values:
            raise SyntaxError(f"`{trait}` needs specialties after `=`.")

        # Stray commas leave empty specialties, which we ignore
        subtraits = [spec for spec in (s.strip() for s in values[0].split(",")) if spec]
        if not subtraits:
            raise SyntaxError(f"`{trait}` needs specialties after `=`.")

        validate_trait_names(trait)
        validate_specialty_names(*subtraits)

        matches.append((trait, subtraits))

    return matches
