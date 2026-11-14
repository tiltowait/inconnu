"""Shared database instance and collections."""

from collections.abc import Awaitable, Callable
from typing import Any

from beanie import Document, init_beanie
from loguru import logger
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession

from config import settings
from models import PostedHeader, RPPost, VChar, VGuild, VUser

_client = AsyncMongoClient(settings.mongo_url, serverSelectionTimeoutMS=1800)
_db = _client.get_database()

# The collections
characters = _db.characters
command_log = _db.command_log
guilds = _db.guilds
headers = _db.headers
rolls = _db.rolls
rp_posts = _db.rp_posts
supporters = _db.supporters
upload_log = _db.upload_log
users = _db.users


def models() -> list[type[Document]]:
    """Beanie database models."""
    return [VChar, RPPost, VGuild, VUser, PostedHeader]


async def server_info() -> dict[str, Any]:
    """Run the client server_info() method and return the result."""
    info = await _client.server_info()
    info["database"] = _db.name  # For logging purposes
    return info


async def transaction[T](callback: Callable[[AsyncClientSession], Awaitable[T]]) -> T:
    """Run the callback in a transaction, committing if it succeeds. Transient
    errors retry the whole callback, so it must be safe to run more than once.
    Pass the session to every database call in it."""
    async with _client.start_session() as session:
        return await session.with_transaction(callback)


async def init():
    """Initialize the database. The models' indexes are the source of truth:
    any other index on their collections is dropped."""
    await init_beanie(_db, document_models=models(), allow_index_dropping=True)
    logger.info("Initialized beanie. Database: {}", _db.name)


async def close():
    """Close the database connection."""
    await _client.close()
    logger.info("Closed MongoDB connection")
