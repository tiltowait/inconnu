"""experience.py - Commands for tracking XP."""

import discord
from discord import option
from discord.commands import SlashCommandGroup, user_command
from discord.ext import commands

import inconnu
from inconnu.options import char_option, player_option


class ExperienceCommands(commands.Cog):
    """A command group for tracking character experience. Only available to server admins."""

    experience = SlashCommandGroup(
        "experience",
        "Experience-tracking commands.",
        contexts={discord.InteractionContextType.guild},
    )

    @user_command(name="Experience Log", contexts={discord.InteractionContextType.guild})
    async def context_experience_list(self, ctx, member: discord.Member):
        """Display the given member's character XP logs."""
        await inconnu.experience.list_events(ctx, None, True, player=member)

    @experience.command()
    @commands.has_permissions(administrator=True)
    @player_option(description="The character's owner", required=True)
    @char_option("The character receiving the XP", required=True)
    @option("amount", description="The amount of XP to give", min_value=1)
    @option("scope", description="Unspent or lifetime XP", choices=["Lifetime", "Unspent"])
    @option("reason", description="The reason for the grant")
    async def award(
        self,
        ctx: discord.ApplicationContext,
        player: discord.Member,
        character: str,
        amount: int,
        scope: str,
        reason: str,
    ):
        """Give experience points to a character."""
        await inconnu.experience.award_or_deduct(
            ctx, character, amount, scope, reason, player=player
        )

    @experience.command()
    @commands.has_permissions(administrator=True)
    @player_option(required=True)
    @char_option("The character from whom to deduct XP", required=True)
    @option("amount", description="The amount of XP to deduct", min_value=1)
    @option("scope", description="Unspent or lifetime XP", choices=["Unspent", "Lifetime"])
    @option("reason", description="The reason for the deduction")
    async def deduct(
        self,
        ctx: discord.ApplicationContext,
        player: discord.Member,
        character: str,
        amount: int,
        scope: str,
        reason: str,
    ):
        """Deduct experience points from a character."""
        await inconnu.experience.award_or_deduct(
            ctx, character, amount * -1, scope, reason, player=player
        )

    experience_remove = experience.create_subgroup("remove", "Remove log entry")

    @experience_remove.command(name="entry")
    @commands.has_permissions(administrator=True)
    @player_option(required=True)
    @char_option("The character whose log to modify", required=True)
    @option(
        "log_index", description="The log entry number (find with /experience log)", min_value=1
    )
    async def remove_entry(
        self,
        ctx: discord.ApplicationContext,
        player: discord.Member,
        character: str,
        log_index: int,
    ):
        """Remove an experience log entry."""
        await inconnu.experience.remove_entry(ctx, character, log_index, player=player)

    @experience.command()
    @char_option("The character whose experience log to show")
    @player_option()
    async def log(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        player: discord.Member,
    ):
        """Display a character's experience log."""
        await inconnu.experience.list_events(ctx, character, False, player=player)

    bulk = SlashCommandGroup(
        "bulk",
        "Bulk experience awarding",
        contexts={discord.InteractionContextType.guild},
    )
    bulk_award = bulk.create_subgroup(
        "award",
        "Bulk experience awarding",
        contexts={discord.InteractionContextType.guild},
    )

    @bulk_award.command(name="xp")
    @commands.has_permissions(administrator=True)
    async def bulk_award_xp(self, ctx):
        """Award experience en masse."""
        await inconnu.experience.bulk_award_xp(ctx)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ExperienceCommands(bot))
