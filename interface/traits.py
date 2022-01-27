"""interface/traits.py - Traits command interface."""

import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

import inconnu


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    _CHARACTER_OPTION = Option(str, "The character to use",
        autocomplete=inconnu.available_characters,
        required=False
    )
    _PLAYER_OPTION = Option(discord.Member, "The character's owner (admin only)", required=False)


    @commands.user_command(name="Traits")
    async def user_traits(self, ctx, user):
        """Display character traits."""
        await self.traits_list(ctx, character=None, player=user)


    traits = SlashCommandGroup("traits", "Character traits commands.")


    @traits.command(name="add")
    @commands.guild_only()
    async def traits_add(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to add. Ex: Oblivion=4 BloodSorcery=2"),
        character: _CHARACTER_OPTION
    ):
        """Add one or more traits to a character. To update, use /traits update."""
        await inconnu.traits.add(ctx, traits, character)


    @traits.command(name="list")
    @commands.guild_only()
    async def traits_list(self, ctx, character: _CHARACTER_OPTION, player: _PLAYER_OPTION):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player)


    @traits.command(name="update")
    @commands.guild_only()
    async def traits_update(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to update. Ex: Oblivion=3"),
        character: _CHARACTER_OPTION
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, traits, character)


    @traits.command(name="delete")
    @commands.guild_only()
    async def delete_traits(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to delete"),
        character: _CHARACTER_OPTION
    ):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, traits, character)
