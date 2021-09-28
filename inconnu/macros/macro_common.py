"""macros/macrocommon.py - Common macro utilities."""

import re

from ..constants import UNIVERSAL_TRAITS
from ..vchar import errors, VChar

NAME_LEN = 50
COMMENT_LEN = 300


def is_macro_name_valid(name: str) -> bool:
    """Determines whether a macro name is valid."""
    return re.match(r"^[A-z_]+$", name) is not None and len(name) < NAME_LEN


def expand_syntax(character: VChar, syntax: str):
    """Validates the pool syntax and replaces elements with full trait names."""
    syntax = re.sub(r"([+-])", r" \g<1> ", syntax) # Make sure there are spaces around all operators
    raw_stack = syntax.split()
    final_stack = []

    expecting_operand = True

    for element in raw_stack:
        if expecting_operand:
            # Expecting a number or a trait
            if element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            if element.isdigit():
                final_stack.append(element)
            else:
                try:
                    trait = character.find_trait(element)
                    final_stack.append(trait.name)
                except errors.TraitNotFoundError as err:
                    universals = []
                    for universal in UNIVERSAL_TRAITS:
                        if universal.startswith(element.lower()):
                            universals.append(universal.title())

                    if len(universals) == 0:
                        raise err
                    if len(universals) > 1:
                        print(universals)
                        raise errors.AmbiguousTraitError(element, universals)

                    final_stack.append(universals[0])

            expecting_operand = False
        else:
            # Expecting an operator
            if not element in ["+", "-"]:
                raise SyntaxError("The macro must use valid pool syntax!")

            final_stack.append(element)
            expecting_operand = True

    return final_stack
