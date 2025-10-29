"""Web interface."""

import asyncio

import uvicorn
from discord.ext import commands
from loguru import logger

import bot


class WebCog(commands.Cog):
    """Starts the FastAPI web server."""

    def __init__(self, bot: bot.InconnuBot):
        self.bot = bot
        self.server_task: asyncio.Task | None = None

    @commands.Cog.listener()
    async def on_connect(self):
        if self.server_task is None:
            # Lazy import to avoid circular dependency with server.py
            from server import app

            config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
            server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(server.serve())
            logger.info("API server started")

    def cog_unload(self):
        if self.server_task:
            self.server_task.cancel()
            logger.info("API server stopped")


def setup(bot: bot.InconnuBot):
    bot.add_cog(WebCog(bot))
