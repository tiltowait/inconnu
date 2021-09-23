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
        return [("You have no characters", "")]

    # Check if they're looking up a player and have lookup permissions
    if "player" in ctx.selected_options:
        owner = ctx.selected_options["player"]
        if owner != ctx.author and not ctx.author.guild_permissions.administrator:
            return [("You do not have admin permissions", "")]
    else:
        owner = ctx.author


    chars = VChar.all_characters(ctx.guild.id, owner.id)
    return [
        (char.name, char.name) for char in chars
            if char.name.lower().startswith(ctx.value_query.lower())
    ]
