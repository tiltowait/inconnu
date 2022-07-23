"""interface/statcord.py - Bot statistics logging cog."""

import os
from logging import DEBUG

import statcord
from discord.ext import commands

from logger import Logger


class StatcordPost(commands.Cog):
    """A simple cog for logging command events."""

    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("STATCORD_TOKEN")

        if self.key is not None:
            Logger.info("BOT: Establishing statcord connection.")
            self.api = statcord.Client(self.bot, self.key)
            self.api.start_loop()
        else:
            self.api = None

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        """Listen to and log command usage."""
        if Logger.level == DEBUG:
            # Log the command for debug purposes
            options = []
            for option in ctx.interaction.data.get("options", []):
                _name = option["name"]
                _value = option["value"]

                if isinstance(_value, str):
                    options.append(f'{_name}="{_value}"')
                else:
                    options.append(f"{_name}={_value}")

            option_string = ", ".join(options) if options else "None"

            Logger.debug(
                "%s: Invoked by %s%s. Options: %s",
                ctx.command.qualified_name.upper(),
                ctx.user.name,
                ctx.user.discriminator,
                option_string,
            )

        if self.key is not None:
            self.api.command_run(ctx)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(StatcordPost(bot))
