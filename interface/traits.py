"""interface/traits.py - Traits command interface."""

import discord
from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog, subslash_cog

import inconnu
from . import debug


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.guild_only()
    @slash_cog(
        name="traits",
        description="Traits command group"
        , guild_ids=debug.WHITELIST
    )
    async def modify_traits(self, ctx):
        """Traits command group start. Unreachable."""


    @ext.check_failure_response("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="traits",
        name="add",
        description="Add one or more traits to a character.",
        options=[
            SlashOption(str, "traits", description="The traits to add", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def add_trait(self, ctx, traits: str, character=None):
        """Add trait(s) to a character."""
        await inconnu.traits.add(ctx, traits, character)


    @ext.check_failure_response("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="traits",
        name="list",
        description="List all of a character's traits.",
        options=[
            SlashOption(str, "character", description="The character to look up"),
            SlashOption(discord.Member, "player", description="The character's owner (admin only)")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def list_traits(self, ctx, character=None, player=None):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player)


    @ext.check_failure_response("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="traits",
        name="update",
        description="Update one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to update", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def update_traits(self, ctx, traits: str, character=None):
        """Update a character's trait(s)."""
        await inconnu.traits.update(ctx, traits, character)


    @ext.check_failure_response("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="traits",
        name="delete",
        description="Delete one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to delete", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def delete_traits(self, ctx, traits: str, character=None):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, traits, character)
