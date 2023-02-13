"""Specialties input tokenizer."""

import re

SYNTAX = "Proper syntax: `trait1=spec1,spec2,spec3 trait2=spec4,spec5` ..."


def tokenize(syntax: str):
    """Normalize and tokenize specialty syntax."""
    if invalid := re.findall(r"[^A-Za-z_\s=,]", syntax):
        invalid = ", ".join(map(lambda t: f"`{t}`", set(invalid)))
        raise SyntaxError(f"Invalid characters: {invalid}")

    # Remove spaces surrounding commas and equals signs
    syntax = re.sub(r"\s*([,=])\s*", r"\1", syntax)

    raw_tokens = syntax.split()
    tokens = []
    for token in raw_tokens:
        if re.match(r"^[A-Za-z_]+=([A-Za-z_]+,?)+$", token) is None:
            raise SyntaxError(f"Invalid token: '{token}'")

        trait, specs = token.split("=", 1)
        specs = specs.strip(",").split(",")
        tokens.append((trait, specs))

    return tokens