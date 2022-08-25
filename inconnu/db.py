"""Shared database instance and collections."""

import os
from typing import Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks import MotorAsyncIOInstance

load_dotenv()

_mongo_url = os.environ["MONGO_URL"]
_db_name = _mongo_url.rsplit("/", 1)[-1]

_client = AsyncIOMotorClient(_mongo_url, serverSelectionTimeoutMS=1800)
_db = _client[_db_name]

# The collections
characters = _db.characters
supporters = _db.supporters
guilds = _db.guilds
headers = _db.headers
log = _db.log
probabilities = _db.probabilities
rolls = _db.rolls
upload_log = _db.upload_log
users = _db.users

instance = MotorAsyncIOInstance(_db)


async def server_info() -> dict[str, Any]:
    """Run the client server_info() method and return the result."""
    info = await _client.server_info()
    info["database"] = _db_name
    return info
