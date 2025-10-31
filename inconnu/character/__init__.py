"""character - Facilities for character CRUD. This package does not contain VChar."""

import re

from inconnu.character import images
from inconnu.character.bio import edit_biography, show_biography
from inconnu.character.convictions import convictions_set, convictions_show
from inconnu.character.create import create
from inconnu.character.delete import delete
from inconnu.character.display import DisplayField, display, display_requested
from inconnu.character.images import upload
from inconnu.character.update import update, update_help

__all__ = (
    "convictions_set",
    "convictions_show",
    "create",
    "delete",
    "display",
    "DisplayField",
    "display_requested",
    "edit_biography",
    "images",
    "show_biography",
    "update",
    "update_help",
    "upload",
    "valid_name",
)


def valid_name(name: str) -> bool:
    """Determine whether a character name is valid."""
    name = " ".join(name.split())
    if not name:
        return False
    return bool(re.match(r"^([^\W]|[-_\s\'])+$", name))
