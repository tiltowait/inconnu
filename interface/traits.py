"""interface/traits.py - Traits command interface."""

from discord.ext import commands

import inconnu
from . import c_help


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.group(
        invoke_without_command=True, name="traits", aliases=["trait", "t"],
        brief = c_help.TRAITS_COMMAND_BRIEF,
        usage = c_help.TRAITS_COMMAND_USAGE,
        help = c_help.TRAITS_COMMAND_HELP
    )
    async def modify_traits(self, ctx, *, args):
        """Traits subcommand start."""
        await ctx.reply(f"Unrecognized command: `{args}`.\nSee `//help traits` for help.")


    @modify_traits.command(
        name="add",
        brief = c_help.TRAITS_ADD_BRIEF,
        usage = c_help.TRAITS_ADD_USAGE,
        help = c_help.TRAITS_ADD_HELP
    )
    async def add_trait(self, ctx, *args):
        """Add trait(s) to a character."""
        await inconnu.traits.add_update.parse(ctx, False, *args)


    @modify_traits.command(
        name="list", aliases=["show", "s"],
        brief = c_help.TRAITS_LIST_BRIEF,
        usage = c_help.TRAITS_LIST_USAGE,
        help = c_help.TRAITS_LIST_HELP
    )
    async def list_traits(self, ctx, *args):
        """Display a character's traits."""
        await inconnu.traits.show.parse(ctx, *args)


    @modify_traits.command(
        name="update",
        brief = c_help.TRAITS_UPDATE_BRIEF,
        usage = c_help.TRAITS_UPDATE_USAGE,
        help = c_help.TRAITS_UPDATE_HELP
    )
    async def update_traits(self, ctx, *args):
        """Update a character's trait(s)."""
        await inconnu.traits.add_update.parse(ctx, True, *args)


    @modify_traits.command(
        name="delete", aliases=["rm"],
        brief = c_help.TRAITS_DELETE_BRIEF,
        usage = c_help.TRAITS_DELETE_USAGE,
        help = c_help.TRAITS_DELETE_HELP
    )
    async def delete_traits(self, ctx, *args):
        """Remove traits from a character."""
        await inconnu.traits.delete.parse(ctx, *args)
