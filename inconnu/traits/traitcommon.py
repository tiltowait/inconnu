"""traits/traitcommon.py - Common functionality across trait operations."""

import re

from inconnu.constants import RESERVED_TRAITS

VALID_TRAIT_PATTERN = re.compile(r"^[A-Za-z_\']+$")


def validate_trait_names(*traits, disciplines=False):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    for trait in traits:
        if (trait_len := len(trait)) > 20:
            raise ValueError(f"`{trait}` is too long by {trait_len - 20} characters.")

        if trait.title() in RESERVED_TRAITS:
            raise ValueError(
                f"`{trait.title()}` is a reserved trait. Use `/character adjust` to set."
            )
        if trait.lower() in RESERVED_TRAITS:
            raise ValueError("Set Hunger with `/character adjust`.")
        if trait.lower() in ["powerbonus", "power_bonus"]:
            raise ValueError("Power bonus is automatic if you roll with a Discipline.")

        if VALID_TRAIT_PATTERN.match(trait) is None:
            term = "Traits" if not disciplines else "Disciplines"
            raise SyntaxError(f"{term} can only have letters and underscores. Invalid: `{trait}`.")
