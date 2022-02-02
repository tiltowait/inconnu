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
        reason: Option(str, "The reason for the grant")
    ):
        """Give experience points to a character."""
        await ctx.respond("Awarding XP")


    @experience.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def deduct(
        self,
        ctx: discord.ApplicationContext,
        player: Option(discord.Member, "The character's owner"),
        character: inconnu.options.character("The character from whom to deduct XP", required=True),
        amount: Option(int, "The amount of XP to deduct", min_value=1),
        reason: Option(str, "The reason for the deduction"),
    ):
        """Deduct experience points from a character."""
        await ctx.respond("Deducting XP")


    @experience.command()
    @commands.guild_only()
    async def list(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to display"),
        player: inconnu.options.player,
    ):
        """Display a character's experience log."""
        await ctx.respond("Displaying the log")


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ExperienceCommands(bot))
