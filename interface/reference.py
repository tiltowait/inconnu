"""interface/reference.py - A cog for reference material."""
# pylint: disable=no-self-use

import asyncio

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu
from logger import Logger


class ReferenceCommands(commands.Cog):
    """A cog for reference commands."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @slash_command()
    async def bp(
        self,
        ctx,
        rating: Option(int, "The Blood Potency rating", choices=inconnu.options.ratings(1, 10)),
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
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk remove rolls from statistics."""
        raw_ids = payload.message_ids
        deletions = []

        for message in payload.cached_messages:
            raw_ids.discard(message.id)
            if message.author == self.bot.user:
                Logger.debug("REFERENCE: Deleting possible roll record")
                deletions.append(message.id)

        Logger.debug("REFERENCE: Blindly deleting %s potential roll records", len(raw_ids))
        deletions.extend(raw_ids)
        if deletions:
            Logger.debug("REFERENCE: Deleting %s potential roll records", len(deletions))
            await inconnu.stats.roll_message_deleted(*deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Remove the roll from statistics."""
        # Check if the message is in the cache
        if (message := raw_message.cached_message) is not None:
            if message.author == self.bot.user:
                Logger.debug("REFERENCE: Deleting possible roll record")
                await inconnu.stats.roll_message_deleted(message.id)
        else:
            # We aren't sure what the message is, so we have no choice but to
            # attempt the deletion.
            Logger.debug("REFERENCE: Blindly deleting potential roll record")
            await inconnu.stats.roll_message_deleted(raw_message.message_id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark all rolls in the deleted channel as deleted."""
        Logger.info(
            "REFERENCE: Deleting all roll records in deleted channel %s (%s)",
            channel.name,
            channel.id,
        )
        await inconnu.stats.delete_rolls_in_channel(channel)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ReferenceCommands(bot))
