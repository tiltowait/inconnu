"""interface/traits.py - Traits command interface."""

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_cog, subslash_cog

import inconnu


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @slash_cog(
        name="traits",
        description="Traits command group"
        #, guild_ids=[882411164468932609] # Enable in Inconnu Support for testing purposes
    )
    @commands.guild_only()
    async def modify_traits(self, ctx):
        """Traits command group start. Unreachable."""


    @subslash_cog(
        base_names="traits",
        name="add",
        description="Add one or more traits to a character.",
        options=[
            SlashOption(str, "traits", description="The traits to add", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        #, guild_ids=[882411164468932609] # Enable in Inconnu Support for testing purposes
    )
    @commands.guild_only()
    async def add_trait(self, ctx, traits: str, character=None):
        """Add trait(s) to a character."""
        await inconnu.traits.add_update.parse(ctx, False, traits, character)


    @subslash_cog(
        base_names="traits",
        name="list",
        description="List all of a character's traits.",
        options=[
            SlashOption(str, "character", description="The character to update")
        ]
        #, guild_ids=[882411164468932609] # Enable in Inconnu Support for testing purposes
    )
    @commands.guild_only()
    async def list_traits(self, ctx, character=None):
        """Display a character's traits."""
        await inconnu.traits.show.parse(ctx, character)


    @subslash_cog(
        base_names="traits",
        name="update",
        description="Update one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to update", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        #, guild_ids=[882411164468932609] # Enable in Inconnu Support for testing purposes
    )
    @commands.guild_only()
    async def update_traits(self, ctx, traits: str, character=None):
        """Update a character's trait(s)."""
        await inconnu.traits.add_update.parse(ctx, True, traits, character)


    @subslash_cog(
        base_names="traits",
        name="delete",
        description="Delete one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to delete", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
        #, guild_ids=[882411164468932609] # Enable in Inconnu Support for testing purposes
    )
    @commands.guild_only()
    async def delete_traits(self, ctx, traits: str, character=None):
        """Remove traits from a character."""
        await inconnu.traits.delete.parse(ctx, traits, character)
