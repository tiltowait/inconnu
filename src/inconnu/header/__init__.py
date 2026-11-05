"""Header imports."""

from inconnu.header import posted
from inconnu.header.show import header_embed as embed
from inconnu.header.show import register_header as register
from inconnu.header.show import show_header
from inconnu.header.update import update_header

__all__ = (
    "embed",
    "header_title",
    "posted",
    "register",
    "show_header",
    "update_header",
)


def header_title(*fields: str | None) -> str:
    """Make a header title out of the given fields."""
    return " • ".join(f for f in fields if f is not None)
