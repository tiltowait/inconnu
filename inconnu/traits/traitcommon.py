"""traits/traitcommon.py - Common functionality across trait operations."""

import re

from ..constants import UNIVERSAL_TRAITS

VALID_TRAIT_PATTERN = re.compile(r"^[A-z_]+$")

def validate_trait_names(*traits):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    for trait in traits:
        if (trait_len := len(trait)) > 20:
            raise ValueError(f"`{trait}` is too long by {trait_len - 20} characters.")

        if trait.lower() in UNIVERSAL_TRAITS:
            raise SyntaxError(f"`{trait}` is a reserved trait and cannot be added/updated/deleted.")

        if VALID_TRAIT_PATTERN.match(trait) is None:
            raise SyntaxError(f"Traits can only have letters and underscores. Received `{trait}`.")
