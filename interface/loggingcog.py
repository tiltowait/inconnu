"""interface/loggingcog.py - Log command events."""

import os
from datetime import datetime

from discord.ext import commands

import inconnu.utils
from logger import Logger


class LoggingCog(commands.Cog):
    """A simple cog for logging command events."""

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        """Log command usage."""
        if ctx.guild is not None:
            location = ctx.guild.name
        else:
            location = "DMs"

        Logger.info(
            "COMMAND: `/%s` invoked by %s (%s) in %s (%s). Options: %s",
            ctx.command.qualified_name,
            ctx.user.name,
            ctx.user.id,
            location,
            ctx.guild_id,
            inconnu.utils.command_options(ctx.interaction),
        )

        # Log to the database
        await inconnu.db.command_log.insert_one(
            {
                "guild": ctx.guild_id,
                "user": ctx.user.id,
                "locale": ctx.interaction.locale,
                "command": ctx.command.qualified_name,
                "options": [
                    {"name": o["name"], "value": o["value"]}
                    for o in ctx.interaction.data.get("options", [])
                ],
                "date": datetime.utcnow(),
            }
        )


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(LoggingCog(bot))
