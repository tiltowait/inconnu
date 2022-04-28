"""interface/reference.py - A cog for reference material."""
# pylint: disable=no-self-use


import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class ReferenceCommands(commands.Cog):
    """A cog for reference commands."""

    @slash_command()
    async def bp(
        self, ctx, rating: Option(int, "The Blood Potency rating", min_value=0, max_value=10)
    ):
        """Look up Blood Potency effects."""
        await inconnu.reference.blood_potency(ctx, rating)

    @slash_command()
    async def cripple(
        self,
        ctx: discord.ApplicationContext,
        damage: Option(int, "The total Aggravated damage sustained", min_value=1),
    ):
        """Generate a random crippling injury based on Aggravated damage."""
        await inconnu.reference.cripple(ctx, damage)

    @slash_command()
    async def probability(
        self,
        ctx: discord.ApplicationContext,
        roll: Option(str, "The pool, hunger, and difficulty"),
        reroll: Option(
            str,
            "The re-roll strategy to use",
            choices=[
                OptionChoice("Re-Roll Failures", "reroll_failures"),
                OptionChoice("Maximize Crits", "maximize_criticals"),
                OptionChoice("Avoid Messy", "avoid_messy"),
                OptionChoice("Risky Avoid Messy", "risky"),
            ],
            required=False,
        ),
        character: inconnu.options.character("The character (if using traits)"),
    ):
        """Calculate outcome probabilities for a given roll."""
        await inconnu.reference.probability(ctx, roll, reroll, character)

    @slash_command()
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.reference.resonance(ctx)

    @slash_command()
    @commands.guild_only()
    async def statistics(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(str, "(Optional) A trait to look for", required=False),
        date: Option(str, "(Optional) YYYYMMDD date to count from", default="19700101"),
    ):
        """View roll statistics for your characters."""
        await inconnu.reference.statistics(ctx, trait, date)

    @slash_command()
    async def temperament(
        self,
        ctx: discord.ApplicationCommand,
        resonance: Option(str, "The resonance being rolled", choices=inconnu.reference.RESONANCES),
    ):
        """Get a random temperament."""
        await inconnu.reference.random_temperament(ctx, resonance)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ReferenceCommands(bot))
