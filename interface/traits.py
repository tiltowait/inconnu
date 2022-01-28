"""interface/traits.py - Traits command interface."""

import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

import inconnu


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.user_command(name="Traits")
    async def user_traits(self, ctx, member):
        """Display character traits."""
        await inconnu.traits.show(ctx, None, member)


    traits = SlashCommandGroup("traits", "Character traits commands.")

    @traits.command(name="add")
    @commands.guild_only()
    async def traits_add(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to add. Ex: Oblivion=4 BloodSorcery=2"),
        character: inconnu.options.character("The character to modify")
    ):
        """Add one or more traits to a character. To update, use /traits update."""
        await inconnu.traits.add(ctx, traits, character)


    @traits.command(name="list")
    @commands.guild_only()
    async def traits_list(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character(),
        player: inconnu.options.player
    ):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player)


    @traits.command(name="update")
    @commands.guild_only()
    async def traits_update(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to update. Ex: Oblivion=3"),
        character: inconnu.options.character("The character to modify")
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, traits, character)


    @traits.command(name="delete")
    @commands.guild_only()
    async def delete_traits(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to delete"),
        character: inconnu.options.character("The character to modify")
    ):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, traits, character)
