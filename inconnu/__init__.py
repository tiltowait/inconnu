"""Set up the package interface."""

import os

from discord.commands import OptionChoice

from . import character
from .cull import Culler as culler
from . import macros
from . import misc
from . import roll
from .settings import Settings as settings
from . import traits
from .vchar import VChar
from . import views


async def available_characters(ctx):
    """Generate a list of the user's available characters."""
    if (guild := ctx.interaction.guild) is None:
        return [OptionChoice("You have no characters", "")]

    # Check if they're looking up a player and have lookup permissions
    user = ctx.interaction.user
    spcs = []

    if (owner := ctx.options.get("player")) is not None:
        if owner != user.id and not user.guild_permissions.administrator:
            return [OptionChoice("You do not have admin permissions", "")]
    else:
        owner = user.id

        if user.guild_permissions.administrator:
            # Add SPCs
            spcs = VChar.all_characters(guild.id, int(os.environ["INCONNU_ID"]))
            spcs = [(spc.name, str(spc.id)) for spc in spcs]

    chars = VChar.all_characters(guild.id, int(owner))
    chars = [(char.name, str(char.id)) for char in chars]
    chars.extend(spcs)

    return [
        OptionChoice(name, ident) for name, ident in chars
            if name.lower().startswith(ctx.value or "")
    ]


def gen_ratings(low, high):
    """Creates a list of OptionChoices within the given range, inclusive."""
    return [OptionChoice(str(n), n) for n in range(low, high + 1)]
