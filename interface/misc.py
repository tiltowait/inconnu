"""interface/misc.py - Miscellaneous commands."""

from discord.ext import commands
from discord_ui import ext
from discord_ui.cogs import slash_cog

import inconnu
from . import debug


class MiscCommands(commands.Cog):
    """Miscellaneous commands."""

    @ext.check_failure_response("Statistics aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="statistics",
        guild_ids=debug.WHITELIST
    )
    async def statistics(self, ctx):
        """View roll statistics for your characters."""
        await inconnu.misc.statistics(ctx)
