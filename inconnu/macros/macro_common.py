"""macros/macrocommon.py - Common macro utilities."""

import re

NAME_LEN = 50
COMMENT_LEN = 300


def is_macro_name_valid(name: str) -> bool:
    """Determines whether a macro name is valid."""
    return re.match(r"^[A-z_]+$", name) is not None and len(name) < NAME_LEN
