"""macros/macrocommon.py - Common macro utilities."""

import re

import errors

NAME_LEN = 50
COMMENT_LEN = 300


def is_macro_name_valid(name: str) -> bool:
    """Validate macro name: letters and underscores only, must contain at least one letter."""
    if len(name) > NAME_LEN or not name:
        return False
    if not re.match(r"^[a-zA-Z_]+$", name):
        return False

    return any(c.isalpha() for c in name)


def check_has_action(pool: list[str], rouses: int):
    """Raise MacroError if the macro would neither roll nor make Rouse Checks."""
    if not pool and rouses == 0:
        raise errors.MacroError("A macro needs a pool or Rouse Checks.")
