"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import signal

import discord
import uvloop
from loguru import logger

import db
import services
from bot import InconnuBot
from config import settings


async def startup():
    """Initialize the database connection and start the bot."""
    await db.init()
    await services.char_mgr.initialize()
    await services.guild_cache.initialize()

    intents = discord.Intents(guilds=True, members=True, messages=True, webhooks=True)
    bot = InconnuBot(intents=intents, debug_guilds=settings.debug_guilds, cache_app_emojis=True)
    try:
        async with bot:
            await bot.start(settings.inconnu_token)
    except KeyboardInterrupt, asyncio.CancelledError:
        logger.info("Received shutdown signal")
    finally:
        logger.info("Cleaning up resources...")
        await services.guild_cache.close()
        await db.close()


def handle_signal(signum: int, _):
    """Handle shutdown signals."""
    signame = signal.Signals(signum).name
    logger.info(f"Received {signame}, initiating shutdown...")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # The signal arrived before or after the event loop ran; nothing to clean up
        raise KeyboardInterrupt

    # Cancel all running tasks to trigger cleanup
    for task in asyncio.all_tasks(loop):
        task.cancel()


def configure_logging():
    """Configure loguru for production (file sink) or leave defaults for dev."""
    if settings.prod:
        logger.remove()
        logger.add(
            "/var/log/inconnu.log",
            rotation="0:00",
            retention=7,
            level="INFO",
        )


def main():
    configure_logging()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        uvloop.run(startup())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
