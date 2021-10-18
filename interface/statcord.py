"""interface/statcord.py - Bot statistics logging cog."""

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
    async def on_command(self, ctx):
        """Listen to and log command usage."""
        self.api.command_run(ctx)
