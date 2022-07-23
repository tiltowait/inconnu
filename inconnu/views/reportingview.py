"""Base Inconnu View."""

import discord

from errorreporter import reporter


class ReportingView(discord.ui.View):
    """A View that reports errors using the Reporter class."""

    async def on_error(self, error, _, interaction: discord.Interaction):
        """Report an error using Reporter functionality."""
        await reporter.report_error(interaction, error)
