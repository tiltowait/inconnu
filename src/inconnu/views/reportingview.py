"""Base Inconnu View."""

import discord

from services.reporter import reporter


class ReportingView(discord.ui.View):
    """A View that reports errors using the Reporter class."""

    async def on_error(self, error, _, interaction: discord.Interaction):  # type:ignore
        """Report an error using Reporter functionality."""
        await reporter.report_error(interaction, error)
