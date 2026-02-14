"""inconnu/cull.py - Cull inactive players and guilds."""

from datetime import UTC, datetime, timedelta

from loguru import logger

import api
import db
import services
from models import VChar


async def cull(days=30):
    """Cull inactive guilds, characters, and macros."""
    logger.info("Initiating culling run.")
    past = datetime.now(UTC) - timedelta(days=days)

    # Remove old guilds

    removed_guilds = []
    guilds = db.guilds.find({"active": False, "left": {"$lt": past}}, {"guild": 1})

    async for guild in guilds:
        guild = guild["guild"]
        removed_guilds.append(guild)
        await db.guilds.delete_one({"guild": guild})

    if removed_guilds:
        logger.info("Culled {} guilds", len(removed_guilds))

    # We remove characters separately so as to make only one database call
    # rather than potentially many

    characters = VChar.find(
        {"$or": [{"guild": {"$in": removed_guilds}}, {"log.left": {"$lt": past}}]}
    )

    async for character in characters:
        await api.delete_character_faceclaims(character)
        if await services.char_mgr.remove(character):
            logger.info("Culling {}", character.name)
        else:
            logger.info("Unable to cull {}", character.name)

    logger.info("Done culling")
