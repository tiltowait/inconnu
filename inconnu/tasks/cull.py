"""inconnu/cull.py - Cull inactive players and guilds."""

from datetime import datetime, timedelta

import api
import inconnu
from logger import Logger


async def cull(days=30):
    """Cull inactive guilds, characters, and macros."""
    Logger.info("CULLER: Initiating culling run.")

    guild_col = inconnu.db.guilds

    past = datetime.utcnow() - timedelta(days=days)

    # Remove old guilds

    removed_guilds = []
    guilds = guild_col.find({"active": False, "left": {"$lt": past}}, {"guild": 1})

    async for guild in guilds:
        guild = guild["guild"]
        removed_guilds.append(guild)
        await guild_col.delete_one({"guild": guild})

    if guilds:
        Logger.info("CULLER: Culled %s guilds", len(removed_guilds))

    # We remove characters separately so as to make only one database call
    # rather than potentially many

    characters = inconnu.models.VChar.find(
        {"$or": [{"guild": {"$in": removed_guilds}}, {"log.left": {"$lt": past}}]}
    )

    async for character in characters:
        await api.delete_character_faceclaims(character)
        if await inconnu.char_mgr.remove(character):
            Logger.info("CULLER: Culling %s", character.name)
        else:
            Logger.info("CULLER: Unable to cull %s", character.name)

    Logger.info("CULLER: Done culling")
