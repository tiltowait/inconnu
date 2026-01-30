"""Base Inconnu View."""

import discord


class ReportingView(discord.ui.View):
    """A View that reports errors using the Reporter class."""

    async def on_error(self, error, _, interaction: discord.Interaction):  # type:ignore
        """Report an error using Reporter functionality."""
        from services.reporter import reporter

        await reporter.report_error(interaction, error)
