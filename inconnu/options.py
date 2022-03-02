"""options.py - Various options for command parameters."""

import os

import discord
from discord.commands import Option, OptionChoice

import inconnu


def ratings(low, high) -> list:
    """Creates a list of OptionChoices within the given range, inclusive."""
    return [OptionChoice(str(n), n) for n in range(low, high + 1)]


def character(description = "The character to use", required=False) -> Option:
    """Return an Option that generates a list of player characters."""
    return Option(str, description,
        autocomplete=_available_characters,
        required=required
    )


player = Option(discord.Member, "The character's owner (admin only)", required=False)


# Helper functions

async def _available_characters(ctx):
    """Generate a list of the user's available characters."""
    if (guild := ctx.interaction.guild) is None:
        return []

    # Check if they're looking up a player and have lookup permissions
    user = ctx.interaction.user
    spcs = []

    if (owner := (ctx.options.get("player") or ctx.options.get("current_owner"))) is not None:
        if owner != user.id and not user.guild_permissions.administrator:
            return [OptionChoice("You do not have admin permissions", "")]
    else:
        owner = user.id

        if user.guild_permissions.administrator:
            # Add SPCs
            spcs = await inconnu.char_mgr.fetchall(guild.id, int(os.environ["INCONNU_ID"]))
            spcs = [(spc.name, spc.id) for spc in spcs]

    chars = await inconnu.char_mgr.fetchall(guild.id, int(owner))
    chars = [(char.name, char.id) for char in chars]
    chars.extend(spcs)

    return [
        OptionChoice(name, ident) for name, ident in chars
            if name.lower().startswith(ctx.value or "")
    ]
