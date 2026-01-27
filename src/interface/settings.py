"""interface/settings.py - Settings-related commands."""

from discord import option
from discord.commands import OptionChoice, slash_command
from discord.ext import commands

import inconnu
from ctx import AppCtx


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

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
        await inconnu.menu(ctx, scope)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(SettingsCommands(bot))
