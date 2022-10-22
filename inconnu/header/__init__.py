"""Header imports."""

from inconnu.header.show import create_header as create
from inconnu.header.show import show_header
from inconnu.header.update import update_header


def header_title(*fields):
    """Make a header title out of the given fields."""
    # This is just a simple wrapper function for join() so we can test length
    return " • ".join(filter(lambda f: f is not None, fields))


def blush_text(character, blush: int) -> str | None:
    """Get the blush text."""
    if character.is_vampire and blush != -1:
        # Only vampires can blush
        return "Blushed" if blush else "Not Blushed"
    return None
