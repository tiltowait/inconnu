"""Set up the package interface."""

from . import character
from . import macros
from . import misc
from . import roll
from .settings import Settings as settings
from . import traits
from .vchar import VChar


async def available_characters(ctx):
    """Generate a list of the user's available characters."""
    if ctx.guild is None:
        return ("You have no characters", "")

    chars = VChar.all_characters(ctx.guild.id, ctx.author.id)
    return [(char.name, char.name) for char in chars]
