"""Database variables."""

import os

import motor.motor_asyncio
from umongo.frameworks import MotorAsyncIOInstance

_mongoclient = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URL"), serverSelectionTimeoutMS=1800
)
_db = _mongoclient.inconnu

# Raw collections
characters = _db.characters
guilds = _db.guilds
log = _db.log
probabilities = _db.probabilities
users = _db.users
rolls = _db.rolls

# Instance used for umongo
instance = MotorAsyncIOInstance(_db)
