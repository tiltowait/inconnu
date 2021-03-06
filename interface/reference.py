"""interface/reference.py - A cog for reference material."""
# pylint: disable=no-self-use

import asyncio

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class ReferenceCommands(commands.Cog):
    """A cog for reference commands."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

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
        style: Option(
            str,
            "Whether to display general success rates or trait successes",
            choices=["Traits", "General"],
        ),
        date: Option(str, "(Optional) YYYYMMDD date to count from", default="19700101"),
        character: inconnu.options.character("The character whose statistics will be looked up"),
        player: inconnu.options.player,
    ):
        """View roll statistics for your characters."""
        await inconnu.reference.statistics(ctx, style, character, date, player)

    @slash_command()
    async def temperament(
        self,
        ctx: discord.ApplicationCommand,
        resonance: Option(str, "The resonance being rolled", choices=inconnu.reference.RESONANCES),
    ):
        """Get a random temperament."""
        await inconnu.reference.random_temperament(ctx, resonance)

    # Roll statistics

    @commands.message_command(name="Toggle Roll Statistics")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def toggle_roll_statistics(self, ctx, message: discord.Message):
        """Toggle whether a roll should be counted for statistical purposes."""
        if ctx.bot.user != message.author:
            await ctx.respond("This isn't an Inconnu roll message.", ephemeral=True)
            return

        toggled = await inconnu.stats.toggle_roll_stats(message.id)
        if toggled is None:
            await ctx.respond(
                "Unable to toggle stats. Either this isn't a roll, or it predates the feature.",
                ephemeral=True,
            )
        else:
            will_or_not = "`WILL`" if toggled else "`WILL NOT`"

            content = "" if toggled else "**This roll `WILL NOT` be included in statistics.**"
            msg = f"[This roll]({message.jump_url}) {will_or_not} be included in statistics."
            embed = discord.Embed(description=msg)

            await asyncio.gather(
                message.edit(content=content),
                ctx.respond(embed=embed, ephemeral=True),
            )

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Remove the roll from statistics."""
        if message.author == self.bot.user:
            await inconnu.stats.roll_message_deleted(message.id)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ReferenceCommands(bot))
