"""experience.py - Commands for tracking XP."""
# pylint: disable=no-self-use, too-many-arguments

import discord
from discord.commands import Option, SlashCommandGroup, user_command
from discord.ext import commands

import inconnu


class ExperienceCommands(commands.Cog):
    """A command group for tracking character experience. Only available to server admins."""

    experience = SlashCommandGroup("experience", "Experience-tracking commands.")

    @user_command(name="Experience Log")
    async def context_experience_list(self, ctx, member: discord.Member):
        """Display the given member's character XP logs."""
        await inconnu.experience.list_events(ctx, None, True, player=member)

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
        reason: Option(str, "The reason for the grant"),
    ):
        """Give experience points to a character."""
        await inconnu.experience.award_or_deduct(
            ctx, character, amount, scope, reason, player=player
        )

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
        await inconnu.experience.award_or_deduct(
            ctx, character, amount * -1, scope, reason, player=player
        )

    experience_remove = experience.create_subgroup("remove", "Remove log entry")

    @experience_remove.command(name="entry")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def remove_entry(
        self,
        ctx: discord.ApplicationContext,
        player: Option(discord.Member, "The character's owner"),
        character: inconnu.options.character("The character whose log to modify", required=True),
        log_index: Option(int, "The log entry number (find with /experience log)", min_value=1),
    ):
        """Remove an experience log entry."""
        await inconnu.experience.remove_entry(ctx, character, log_index, player=player)

    @experience.command()
    @commands.guild_only()
    async def log(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character whose experience log to show"),
        player: inconnu.options.player,
    ):
        """Display a character's experience log."""
        await inconnu.experience.list_events(ctx, character, False, player=player)

    bulk = SlashCommandGroup("bulk", "Bulk experience awarding")
    bulk_award = bulk.create_subgroup("award", "Bulk experience awarding")

    @bulk_award.command(name="xp")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def bulk_award_xp(self, ctx):
        """Award experience en masse."""
        await inconnu.experience.bulk_award_xp(ctx)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ExperienceCommands(bot))
