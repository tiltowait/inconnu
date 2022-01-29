"""interface/statcord.py - Bot statistics logging cog."""

import os

from discord.ext import commands

import statcord


class StatcordPost(commands.Cog):
    """A simple cog for logging command events."""

    def __init__(self, bot, key):
        self.bot = bot
        self.key = key
        self.api = statcord.Client(self.bot, self.key)
        self.api.start_loop()


    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        """Listen to and log command usage."""
        self.api.command_run(ctx)


def setup(bot):
    """Add the cog to the bot."""
    if (statcord_token := os.getenv("STATCORD_TOKEN")) is not None:
        print("Establishing statcord connection.")
        bot.add_cog(StatcordPost(bot, statcord_token))
