"""interface/misc.py - Miscellaneous commands."""

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    @slash_cog(name="coinflip", guild_ids=debug.WHITELIST)
    async def coinflip(self, ctx):
        """Flip a coin."""
        await inconnu.misc.coinflip(ctx)


    @slash_cog(
        name="percentile",
        options=[SlashOption(int, "ceiling", description="The roll's highest possible value")],
        guild_ids=debug.WHITELIST
    )
    async def percentile(self, ctx, ceiling=100):
        """Roll between 1 and a given ceiling (default 100)."""
        await inconnu.misc.percentile(ctx, ceiling)


    @slash_cog(
        name="probability",
        options=[
            SlashOption(str, "roll", description="The pool, hunger, and difficulty", required=True),
            SlashOption(str, "reroll",
                description="The re-roll strategy to use",
                choices=[
                    ("Re-roll Failures", "reroll_failures"),
                    ("Maximize Crits", "maximize_criticals"),
                    ("Avoid Messy", "avoid_messy"),
                    ("Risky Avoid Messy", "risky")
                ]
            ),
            SlashOption(str, "character", description="The character if using traits",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def probabilities(self, ctx, roll: str, reroll=None, character=None):
        """Calculate outcome probabilities for a given roll."""
        await inconnu.misc.probability(ctx, roll, reroll, character)


    @ext.check_failure_response("Statistics aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="statistics",
        guild_ids=debug.WHITELIST
    )
    async def statistics(self, ctx):
        """View roll statistics for your characters."""
        await inconnu.misc.statistics(ctx)
