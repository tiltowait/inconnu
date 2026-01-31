"""Shared database instance and collections."""

import os
from typing import Any

from beanie import Document, init_beanie
from dotenv import load_dotenv
from loguru import logger
from pymongo import AsyncMongoClient

from models import RPPost, VChar, VGuild, VUser

load_dotenv()

_mongo_url = os.environ["MONGO_URL"]
_db_name = _mongo_url.rsplit("/", 1)[-1]

_client = AsyncMongoClient(_mongo_url, serverSelectionTimeoutMS=1800)
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


def models() -> list[type[Document]]:
    """Beanie database models."""
    return [VChar, RPPost, VGuild, VUser]


async def server_info() -> dict[str, Any]:
    """Run the client server_info() method and return the result."""
    info = await _client.server_info()
    info["database"] = _db_name  # For logging purposes
    return info


async def init():
    """Initialize the database."""
    await init_beanie(_db, document_models=models())
    logger.info("Initialized beanie")


async def close():
    """Close the database connection."""
    await _client.close()
    logger.info("Closed MongoDB connection")
