"""interface/errorlistener.py - Report errors from commands, views, and modals."""

from typing import cast

import discord
from discord.ext import commands

from bot import InconnuBot
from ctx import AppCtx, AppInteraction
from services.reporter import ErrorReporter


class ErrorListener(commands.Cog):
    """Sends command, view, and modal errors to the error reporter."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot
        self.reporter = ErrorReporter(bot)

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """Report a command error."""
        await self.reporter.report_error(cast(AppCtx, ctx), error)

    @commands.Cog.listener()
    async def on_view_error(
        self, error: Exception, _: discord.ui.ViewItem, interaction: discord.Interaction
    ):
        """Report an error from a view's component or interaction check."""
        await self.reporter.report_error(cast(AppInteraction, interaction), error)

    @commands.Cog.listener()
    async def on_modal_error(self, error: Exception, interaction: discord.Interaction):
        """Report an error from a modal's callback."""
        await self.reporter.report_error(cast(AppInteraction, interaction), error)


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(ErrorListener(bot))
