"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import signal

import uvloop
from dotenv import load_dotenv
from loguru import logger

import db
import services
from bot import bot
from config import BOT_TOKEN, PROD

load_dotenv()


async def startup():
    """Initialize the database connection and start the bot."""
    await db.init()
    await services.char_mgr.initialize()
    try:
        async with bot:
            await bot.start(BOT_TOKEN)
    finally:
        await db.close()


def handle_signal(signum: int, _):
    """Handle shutdown signals."""
    signame = signal.Signals(signum).name
    logger.info(f"Received {signame}, shutting down...")
    raise KeyboardInterrupt


def main():
    uvloop.install()
    logger.info("Installed uvloop")

    if PROD:
        logger.debug("Configuring log rotation")
        logger.remove()
        logger.add(
            "/var/log/inconnu.log",
            rotation="0:00",
            retention=7,
            level="INFO",
        )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(startup())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
