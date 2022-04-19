"""Set up the package interface."""

import os

import discord
import motor.motor_asyncio

from . import character
from . import cull as culler
from . import (experience, log, macros, misc, options, reference, settings,
               stats, traits, utils, views)
from .roll import Roll
from .vchar import CharacterManager, VChar

char_mgr = CharacterManager()
settings = settings.Settings()

_mongoclient = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URL"), serverSelectionTimeoutMS=1800
)
db = _mongoclient.inconnu


async def get_message(inter):
    """Get the message from an interaction."""
    if isinstance(inter, discord.Message):
        return inter
    return await inter.original_message()


def respond(ctx):
    """Get the proper response callable."""
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            return ctx.followup.send
        return ctx.response.send_message
    return ctx.respond


def gen_timestamp(date, style=None):
    """Generate a Discord timestamp object."""
    timestamp = int(date.timestamp())
    if style:
        terminator = ":" + style
    else:
        terminator = ""
    return f"<t:{timestamp}{terminator}>"


def get_avatar(user: discord.User | discord.Member):
    """Get the user's avatar."""
    if isinstance(user, discord.User):
        # Users don't have a guild presence
        return user.display_avatar

    # Members can have a guild-specific avatar
    return user.guild_avatar or user.display_avatar
