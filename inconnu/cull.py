"""inconnu/cull.py - Cull inactive players and guilds."""

import os
from datetime import datetime, timedelta

import motor.motor_asyncio

import inconnu


async def cull(days=30):
    """Cull inactive guilds, characters, and macros."""
    print("Initiating culling run.")

    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URL"))
    char_col = client.inconnu.characters
    guild_col = client.inconnu.guilds

    past = datetime.utcnow() - timedelta(days=days)

    # Remove old guilds

    removed_guilds = []
    guilds = guild_col.find({ "active": False, "left": { "$lt": past } }, { "guild": 1 })

    async for guild in guilds:
        guild = guild["guild"]
        removed_guilds.append(guild)
        await guild_col.delete_one({ "guild": guild })

    if guilds:
        print(f"Culled {len(removed_guilds)} guilds.")

    # We remove characters separately so as to make only one database call
    # rather than potentially many

    characters = char_col.find({
        "$or": [
            { "guild": { "$in": removed_guilds } },
            { "log.left": { "$lt": past } }
        ]
    })

    async for char_params in characters:
        character = inconnu.VChar(char_params)
        if await inconnu.char_mgr.remove(character):
            print(f"Culling {character.name}.")
        else:
            print(f"Unable to cull {character.name}.")

    print("Done culling.")
