"""Set up the package interface."""

import os

import discord
import motor.motor_asyncio

from . import character
from . import cull as culler
from . import experience
from . import log
from . import macros
from . import misc
from . import options
from .roll import Roll
from .settings import Settings as settings
from . import stats
from . import traits
from .vchar import CharacterManager, VChar
from . import views

char_mgr = CharacterManager()

mongoclient = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URL"),
    serverSelectionTimeoutMS=1800
)

def respond(ctx):
    """Get the proper response callable."""
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            return ctx.followup.send
        return ctx.response.send_message
    return ctx.respond
