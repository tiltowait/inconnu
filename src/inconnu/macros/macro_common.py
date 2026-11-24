"""macros/macrocommon.py - Common macro utilities."""

import errors
from utils.validation import (
    MAX_MACRO_COMMENT_LENGTH,
    MAX_MACRO_NAME_LENGTH,
    VALID_MACRO_NAME_PATTERN,
)

NAME_LEN = MAX_MACRO_NAME_LENGTH
COMMENT_LEN = MAX_MACRO_COMMENT_LENGTH


def is_macro_name_valid(name: str) -> bool:
    """Validate macro name: letters and underscores only, must contain at least one letter."""
    # $ alone would allow a trailing newline
    return len(name) <= NAME_LEN and VALID_MACRO_NAME_PATTERN.fullmatch(name) is not None


def check_has_action(pool: list[str], rouses: int):
    """Raise MacroError if the macro would neither roll nor make Rouse Checks."""
    if not pool and rouses == 0:
        raise errors.MacroError("A macro needs a pool or Rouse Checks.")
