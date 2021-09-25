"""Set up the package interface."""

import os

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
    spcs = []

    if "player" in ctx.selected_options:
        owner = ctx.selected_options["player"]
        if owner != ctx.author and not ctx.author.guild_permissions.administrator:
            return [("You do not have admin permissions", "")]
    else:
        owner = ctx.author

        if ctx.author.guild_permissions.administrator:
            # Add SPCs
            spcs = VChar.all_characters(ctx.guild.id, os.environ["INCONNU_ID"])
            spcs = [(f"{spc.name} (SPC)", str(spc.id)) for spc in spcs]

    chars = VChar.all_characters(ctx.guild.id, owner.id)
    chars = [(char.name, str(char.id)) for char in chars]
    chars.extend(spcs)

    return [
        (name, ident) for name, ident in chars
            if name.lower().startswith(ctx.value_query.lower())
    ]
