"""Web interface."""

import asyncio
import socket
from typing import TYPE_CHECKING

import uvicorn
from discord.ext import commands
from loguru import logger

from config import settings
from events import char_events

if TYPE_CHECKING:
    from bot import InconnuBot


class APIServer(uvicorn.Server):
    """A uvicorn server that ends event streams when it shuts down."""

    async def startup(self, sockets: list[socket.socket] | None = None):
        """Allow event streams, which an earlier server may have closed."""
        char_events.open()
        await super().startup(sockets)

    async def shutdown(self, sockets: list[socket.socket] | None = None):
        """End the event streams, which never finish on their own, so the
        graceful shutdown needn't time out waiting for them."""
        char_events.close()
        await super().shutdown(sockets)


class WebCog(commands.Cog):
    """Starts the FastAPI web server."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot
        self.server: APIServer | None = None
        # Only a strong reference, so the running server isn't garbage
        # collected; use self.server to check or stop it
        self.server_task: asyncio.Task | None = None

    @commands.Cog.listener()
    async def on_connect(self):
        """Start the API server on first connect."""
        if self.server is None:
            # Lazy import to avoid circular dependency with server.py
            from server import app

            app.state.bot = self.bot
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=8000,
                loop="asyncio",
                log_level=None if settings.prod else "debug",
                # A backstop: APIServer ends the event streams at shutdown
                timeout_graceful_shutdown=5,
            )
            self.server = APIServer(config)
            self.server_task = asyncio.create_task(self.server.serve())
            logger.info("API server started")

    def cog_unload(self):
        """Stop the API server. Graceful, not cancelled, so the server's
        shutdown ends the event streams."""
        if self.server:
            self.server.should_exit = True
            logger.info("API server stopping")


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(WebCog(bot))
