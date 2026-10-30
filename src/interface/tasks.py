"""interface/tasks.py - Scheduled maintenance tasks."""

from datetime import UTC, time
from typing import TYPE_CHECKING

from discord.ext import commands, tasks
from loguru import logger

import tasks as bot_tasks

if TYPE_CHECKING:
    from bot import InconnuBot


class TasksCog(commands.Cog):
    """Runs scheduled maintenance tasks."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the tasks on first connection."""
        for loop in (self.cull_inactive, self.check_premium_expiries):
            if not loop.is_running():
                loop.start()
                logger.info("Started task: {}", loop.coro.__name__)

    def cog_unload(self):
        """Stop the tasks."""
        self.cull_inactive.cancel()
        self.check_premium_expiries.cancel()

    @tasks.loop(time=time(12, 0, tzinfo=UTC))
    async def cull_inactive(self):
        """Cull inactive characters and guilds."""
        await bot_tasks.cull()

    @tasks.loop(time=time(0, tzinfo=UTC))
    async def check_premium_expiries(self):
        """Remove images from expired supporters."""
        await bot_tasks.premium.remove_expired_images()


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(TasksCog(bot))
