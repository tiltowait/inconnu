"""interface/settings.py - Settings-related commands."""

from typing import TYPE_CHECKING

from discord import option
from discord.commands import OptionChoice, slash_command

import inconnu
from ctx import AppCtx
from interface import CommandCog
from utils.urls import docs_url

if TYPE_CHECKING:
    from bot import InconnuBot


class SettingsCommands(CommandCog, name="Settings"):  # pyright: ignore[reportCallIssue, reportGeneralTypeIssues]
    """Change your settings and your server's."""

    docs = {"Documentation": docs_url("advanced/server-settings")}

    @slash_command()
    @option(
        "scope",
        description="Show/edit settings for yourself or the server.",
        choices=[
            OptionChoice("Yourself", "self"),
            OptionChoice("Server", "guild"),
        ],
    )
    async def settings(self, ctx: AppCtx, scope: str):
        """Adjust user/server settings."""
        await inconnu.menu.show(ctx, scope)


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(SettingsCommands(bot))
