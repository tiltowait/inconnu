"""interface/loggingcog.py - Log command events."""

import os
from logging import DEBUG

import statcord
from discord.ext import commands

import inconnu.utils
from logger import Logger


class LoggingCog(commands.Cog):
    """A simple cog for logging command events."""

    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("STATCORD_TOKEN")

        if self.key is not None:
            Logger.info("BOT: Establishing statcord connection")
            self.api = statcord.Client(self.bot, self.key)
            self.use_statcord = True
            self.api.start_loop()
        else:
            Logger.warning("BOT: Statcord not configured")
            self.api = None
            self.use_statcord = False

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        """Log command usage."""
        if ctx.guild is not None:
            location = ctx.guild.name
        else:
            location = "DMs"

        Logger.info(
            "COMMAND: `/%s` invoked by %s#%s in %s. Options: %s",
            ctx.command.qualified_name,
            ctx.user.name,
            ctx.user.discriminator,
            location,
            inconnu.utils.command_options(ctx.interaction),
        )

        if self.use_statcord:
            self.api.command_run(ctx)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(LoggingCog(bot))
