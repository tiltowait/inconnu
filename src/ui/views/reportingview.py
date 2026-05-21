"""Base Inconnu View."""

import discord

from ctx import AppInteraction


class ReportingView(discord.ui.View):
    """A View that reports errors using the Reporter class."""

    async def on_error(self, error, _, interaction: AppInteraction):  # type:ignore
        """Report an error using Reporter functionality."""
        from services.reporter import reporter

        await reporter.report_error(interaction, error)
