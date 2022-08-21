"""character - Facilities for character CRUD. This package does not contain VChar."""

import re

from .bio import edit_biography, show_biography
from .convictions import convictions_set, convictions_show
from .create import create
from .delete import delete
from .display import DisplayField, display, display_requested
from .images import upload
from .update import update, update_help


def valid_name(name: str) -> bool:
    """Determine whether a character name is valid."""
    return bool(re.match(r"^([^\W]|[-_\s\'])+$", name))
