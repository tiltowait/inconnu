"""interface/misc.py - Miscellaneous commands."""

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    @slash_command()
    async def coinflip(self, ctx):
        """Flip a coin."""
        await inconnu.misc.coinflip(ctx)


    @slash_command()
    async def random(
        self,
        ctx: discord.ApplicationContext,
        ceiling: Option(int, "The roll's highest possible value", min_value=0, default=100)
    ):
        """Roll between 1 and a given ceiling (default 100)."""
        await inconnu.misc.percentile(ctx, ceiling)


    @slash_command()
    async def probability(
        self,
        ctx: discord.ApplicationContext,
        roll: Option(str, "The pool, hunger, and difficulty"),
        reroll: Option(str, "The re-roll strategy to use",
            choices=[
                OptionChoice("Re-roll Failures", "reroll_failures"),
                OptionChoice("Maximize Crits", "maximize_criticals"),
                OptionChoice("Avoid Messy", "avoid_messy"),
                OptionChoice("Risky Avoid Messy", "risky")
            ],
            required=False
        ),
        character: inconnu.options.character("The character (if using traits)")
    ):
        """Calculate outcome probabilities for a given roll."""
        await inconnu.misc.probability(ctx, roll, reroll, character)


    @slash_command()
    @commands.guild_only()
    async def statistics(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(str, "(Optional) A trait to look for", required=False),
        date: Option(str, "(Optional) YYYYMMDD date to count from", default="19700101")
    ):
        """View roll statistics for your characters."""
        await inconnu.misc.statistics(ctx, trait, date)
