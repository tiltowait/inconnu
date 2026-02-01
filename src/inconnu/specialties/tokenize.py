"""Specialties input tokenizer."""

from pyparsing import DelimitedList, Group, OneOrMore, ParseException, Word, alphas

from utils.validation import validate_specialty_names, validate_trait_names

SYNTAX = "```trait1=spec1 trait2=spec2,spec3 ...```"


def tokenize(syntax: str) -> list[tuple[str, list[str]]]:
    """Tokenize subtrait syntax."""
    alphascore = alphas + "_"
    trait_group = OneOrMore(
        Group(
            Word(alphascore).set_results_name("trait")
            + "="
            + DelimitedList(Word(alphascore), allow_trailing_delim=True).set_results_name(
                "subtraits"
            )
        )
    )

    try:
        matches = []
        for match in trait_group.parse_string(syntax, parse_all=True):
            match = match.as_dict()
            trait = match["trait"]
            subtraits = match["subtraits"]

            # Validate trait and specialty names
            validate_trait_names(trait)
            validate_specialty_names(*subtraits)

            matches.append((trait, subtraits))
        return matches

    except ParseException as err:
        raise SyntaxError(err) from err
