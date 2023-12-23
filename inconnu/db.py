"""Shared database instance and collections."""

import os
from typing import Any

from beanie import init_beanie
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks import MotorAsyncIOInstance

import inconnu

load_dotenv()

_mongo_url = os.environ["MONGO_URL"]
_db_name = _mongo_url.rsplit("/", 1)[-1]

_client = AsyncIOMotorClient(_mongo_url, serverSelectionTimeoutMS=1800)
_db = _client[_db_name]

# The collections
characters = _db.characters
command_log = _db.command_log
guilds = _db.guilds
headers = _db.headers
interactions = _db.interactions
log = _db.log
probabilities = _db.probabilities
rolls = _db.rolls
rp_posts = _db.rp_posts
supporters = _db.supporters
upload_log = _db.upload_log
users = _db.users

instance = MotorAsyncIOInstance(_db)


async def server_info() -> dict[str, Any]:
    """Run the client server_info() method and return the result."""
    info = await _client.server_info()
    info["database"] = _db_name  # For logging purposes
    return info


async def init_db(db=None):
    """Initialize the database, collections and models."""
    if db is None:
        mongo_url = os.environ["MONGO_URL"]
        db_name = _mongo_url.rsplit("/", 1)[-1]
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]

    await init_beanie(db, document_models=[inconnu.VGuild, inconnu.VUser])
