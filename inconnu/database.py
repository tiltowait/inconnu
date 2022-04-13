"""Database variables."""

import os

import motor.motor_asyncio
from umongo.frameworks import MotorAsyncIOInstance

_mongoclient = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URL"), serverSelectionTimeoutMS=1800
)
db = _mongoclient.inconnu

# Raw collections
characters = db.characters
guilds = db.guilds
log = db.log
probabilities = db.probabilities
users = db.users
rolls = db.rolls

# Instance used for umongo
instance = MotorAsyncIOInstance(db)
