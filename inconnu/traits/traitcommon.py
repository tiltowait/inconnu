"""traits/traitcommon.py - Common functionality across trait operations."""

import re

from ..constants import UNIVERSAL_TRAITS

VALID_TRAIT_PATTERN = re.compile(r"^[A-z_]+$")


def validate_trait_names(*traits, specialties=False):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    for trait in traits:
        if (trait_len := len(trait)) > 20:
            raise ValueError(f"`{trait}` is too long by {trait_len - 20} characters.")

        if trait.title() in UNIVERSAL_TRAITS:
            raise SyntaxError(
                f"`{trait.title()}` is a reserved trait. Use `/character adjust` to set."
            )

        if VALID_TRAIT_PATTERN.match(trait) is None:
            term = "Traits" if not specialties else "Specialties"
            raise SyntaxError(f"{term} can only have letters and underscores. Invalid: `{trait}`.")
