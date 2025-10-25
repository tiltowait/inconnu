"""interface/reference.py - A cog for reference material."""
# pylint: disable=no-self-use

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands
from loguru import logger

import inconnu
import interface


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

    @slash_command(contexts={discord.InteractionContextType.guild})
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
        await inconnu.reference.statistics(ctx, character, style, date, player=player)

    @slash_command()
    async def temperament(
        self,
        ctx: discord.ApplicationContext,
        resonance: Option(str, "The resonance being rolled", choices=inconnu.reference.RESONANCES),
    ):
        """Get a random temperament."""
        await inconnu.reference.random_temperament(ctx, resonance)

    # Roll statistics

    @commands.message_command(
        name="Toggle Roll Statistics", contexts={discord.InteractionContextType.guild}
    )
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
            will_or_not = "will" if toggled else "will not"

            content = "" if toggled else "This roll **will not** be included in statistics."
            msg = f"[This roll]({message.jump_url}) **{will_or_not}** be included in statistics."
            embed = discord.Embed(description=msg)

            try:
                await message.edit(content=content)
                await ctx.respond(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await inconnu.utils.error(
                    ctx,
                    f"{ctx.bot.user.mention} needs the `View Messages` "
                    "permission to edit the message. If this is a thread, then "
                    "make sure it's unlocked.",
                    (" ", f"[Jump to message.]({message.jump_url})"),
                    footer="The roll statistics were still toggled! Running "
                    "the command again will undo what you just did.",
                    title="Roll stats toggled but unable to edit message",
                )

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk remove rolls from statistics."""
        # We only need the message IDs
        deletions = interface.raw_bulk_delete_handler(payload, self.bot, lambda id: id)
        if deletions:
            logger.debug("REFERENCE: Deleting {} potential roll records", len(deletions))
            await inconnu.stats.roll_message_deleted(*deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Remove the roll from statistics."""

        async def deletion_handler(message_id: int):
            """Handler that performs the actual database write."""
            logger.debug("REFERENCE: Deleting possible roll record")
            await inconnu.stats.roll_message_deleted(message_id)

        await interface.raw_message_delete_handler(raw_message, self.bot, deletion_handler)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark all rolls in the deleted channel as deleted."""
        logger.info(
            "REFERENCE: Deleting all roll records in deleted channel %s (%s)",
            channel.name,
            channel.id,
        )
        await inconnu.stats.delete_rolls_in_channel(channel)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(ReferenceCommands(bot))
