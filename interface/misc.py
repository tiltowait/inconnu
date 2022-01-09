"""interface/misc.py - Miscellaneous commands."""

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_command

import inconnu
from . import debug


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    @slash_command(name="coinflip", guild_ids=debug.WHITELIST)
    async def coinflip(self, ctx):
        """Flip a coin."""
        await inconnu.misc.coinflip(ctx)


    @slash_command(
        name="percentile",
        options=[SlashOption(int, "ceiling", description="The roll's highest possible value")],
        guild_ids=debug.WHITELIST
    )
    @ext.alias(["random"])
    async def percentile(self, ctx, ceiling=100):
        """Roll between 1 and a given ceiling (default 100)."""
        await inconnu.misc.percentile(ctx, ceiling)


    @slash_command(
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


    @ext.check_failed("Statistics aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
        name="statistics",
        options=[
            SlashOption(str, "trait", description="(Optional) A trait to look for"),
            SlashOption(str, "date", description="(Optional) YYYYMMDD date to count from")
        ],
        guild_ids=debug.WHITELIST
    )
    async def statistics(self, ctx, trait=None, date="19700101"):
        """View roll statistics for your characters."""
        await inconnu.misc.statistics(ctx, trait, date)
