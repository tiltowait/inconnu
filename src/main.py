"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import os

import uvloop
from dotenv import load_dotenv
from loguru import logger

import db
from bot import bot

load_dotenv()


async def startup():
    """Initialize the database connection and start the bot."""
    await db.init()
    async with bot:
        await bot.start(os.environ["INCONNU_TOKEN"])


def main():
    uvloop.install()
    logger.info("Installed uvloop")
    asyncio.run(startup())


if __name__ == "__main__":
    main()
