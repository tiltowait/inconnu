"""Header imports."""

from inconnu.header import posted
from inconnu.header.show import header_embed as embed
from inconnu.header.show import register_header as register
from inconnu.header.show import show_header
from inconnu.header.update import update_header
from models import VChar

__all__ = (
    "blush_text",
    "posted",
    "embed",
    "header_title",
    "register",
    "show_header",
    "update_header",
)


def header_title(*fields: str | None):
    """Make a header title out of the given fields."""
    return " • ".join(f for f in fields if f is not None)


def blush_text(character: VChar, blush: int) -> str | None:
    """Get the blush text."""
    if character.is_vampire and blush != -1:
        # Only vampires can blush
        return "Blushed" if blush else "Not Blushed"
    return None
