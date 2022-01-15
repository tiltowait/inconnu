"""interface/traits.py - Traits command interface."""

import discord
from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import subslash_command, context_command

import inconnu
from . import debug


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @context_command(
        name="Traits",
        type="user",
        guild_ids=debug.WHITELIST
    )
    async def user_traits(self, ctx, user):
        """Display character traits."""
        await self.list_traits(ctx, player=user)


    @ext.check_failed("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="traits",
        name="add",
        description="Add one or more traits to a character.",
        options=[
            SlashOption(str, "traits", description="The traits to add", required=True),
            SlashOption(str, "character", description="The character to update",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def add_trait(self, ctx, traits: str, character=None):
        """Add trait(s) to a character."""
        await inconnu.traits.add(ctx, traits, character)


    @ext.check_failed("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="traits",
        name="list",
        description="List all of a character's traits.",
        options=[
            SlashOption(str, "character", description="The character to look up",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player", description="The character's owner (admin only)")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def list_traits(self, ctx, character=None, player=None):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player)


    @ext.check_failed("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="traits",
        name="update",
        description="Update one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to update", required=True),
            SlashOption(str, "character", description="The character to update",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def update_traits(self, ctx, traits: str, character=None):
        """Update a character's trait(s)."""
        await inconnu.traits.update(ctx, traits, character)


    @ext.check_failed("Characters and traits aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="traits",
        name="delete",
        description="Delete one or more traits.",
        options=[
            SlashOption(str, "traits", description="The traits to delete", required=True),
            SlashOption(str, "character", description="The character to update",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def delete_traits(self, ctx, traits: str, character=None):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, traits, character)
