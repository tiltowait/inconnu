"""experience.py - Commands for tracking XP."""

import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

import inconnu


class ExperienceCommands(commands.Cog):
    """A command group for tracking character experience. Only available to server admins."""

    experience = SlashCommandGroup("experience", "Experience-tracking commands.")


    @experience.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def award(
        self,
        ctx: discord.ApplicationContext,
        player: Option(discord.Member, "The character's owner"),
        character: inconnu.options.character("The character receiving the XP", required=True),
        amount: Option(int, "The amount of XP to give", min_value=1),
        scope: Option(str, "Unspent or lifetime XP", choices=["Lifetime", "Unspent"]),
        reason: Option(str, "The reason for the grant")
    ):
        """Give experience points to a character."""
        await inconnu.experience.award_or_deduct(ctx, player, character, amount, scope, reason)


    @experience.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def deduct(
        self,
        ctx: discord.ApplicationContext,
        player: Option(discord.Member, "The character's owner"),
        character: inconnu.options.character("The character from whom to deduct XP", required=True),
        amount: Option(int, "The amount of XP to deduct", min_value=1),
        scope: Option(str, "Unspent or lifetime XP", choices=["Unspent", "Lifetime"]),
        reason: Option(str, "The reason for the deduction"),
    ):
        """Deduct experience points from a character."""
        await inconnu.experience.award_or_deduct(ctx, player, character, amount * -1, scope, reason)


    @experience.command()
    @commands.guild_only()
    async def list(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to display"),
        player: inconnu.options.player,
    ):
        """Display a character's experience log."""
        await inconnu.experience.list_events(ctx, character, player)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ExperienceCommands(bot))
