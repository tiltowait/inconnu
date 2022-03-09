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
from . import reference
from .roll import Roll
from . import settings
from . import stats
from . import traits
from . import utils
from .vchar import CharacterManager, VChar
from . import views

char_mgr = CharacterManager()
settings = settings.Settings()

_mongoclient = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URL"),
    serverSelectionTimeoutMS=1800
)
db = _mongoclient.inconnu


def response(ctx):
    """Get the response or, if it's been responded to, the followup."""
    if ctx.response.is_done():
        return ctx.followup
    return ctx.response


def respond(ctx):
    """Get the proper response callable."""
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            return ctx.followup.send
        return ctx.response.send_message
    return ctx.respond


def fence(string: str) -> str:
    """Surround the string in a code fence. Useful for map()."""
    return f"`{string}`"
