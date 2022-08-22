"""Shared database instance and collections."""

import os
from typing import Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

_client = AsyncIOMotorClient(os.getenv("MONGO_URL"), serverSelectionTimeoutMS=1800)
_db = _client[os.environ["MONGO_DB"]]

# The collections
characters = _db.characters
guilds = _db.guilds
headers = _db.headers
log = _db.log
probabilities = _db.probabilities
rolls = _db.rolls
upload_log = _db.upload_log
users = _db.users


async def server_info() -> dict[str, Any]:
    """Run the client server_info() method and return the result."""
    return await _client.server_info()
