"""traits/traitcommon.py - Common functionality across trait operations."""

import re

VALID_TRAIT_PATTERN = re.compile(r"^[A-z_]+$")

def validate_trait_names(*traits):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    for trait in traits:
        if VALID_TRAIT_PATTERN.match(trait) is None:
            raise SyntaxError(f"Traits can only have letters and underscores. Received `{trait}`")
