"""Primary Inconnu import."""

import os
from typing import List

import discord
from numpy.random import default_rng

import config
from inconnu import (
    character,
    db,
    errors,
    experience,
    header,
    log,
    macros,
    misc,
    models,
    options,
    reference,
    settings,
    stats,
    tasks,
    traits,
    utils,
    views,
)
from inconnu.emoji import emojis
from inconnu.models import CharacterManager
from inconnu.roll import Roll

char_mgr = CharacterManager()
settings = settings.Settings()
bot = None

_rng = default_rng()


def d10(count: int = None) -> List[int] | int:
    """Generate one or a list of d10s."""
    if count is None:
        return int(_rng.integers(1, 11))
    return list(map(int, _rng.integers(1, 11, count)))


def random(ceiling=100):
    """Get a random number between 1 and ceiling."""
    return _rng.integers(1, ceiling + 1)


def fence(string: str):
    """Add a code fence around a string."""
    return f"`{string}`"


async def get_message(inter):
    """Get the message from an interaction."""
    if isinstance(inter, discord.Message):
        return inter
    return await inter.original_response()


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


def profile_url(charid: str) -> str:
    """Generate a profile URL for the character."""
    return config.PROFILE_SITE + f"profile/{charid}"
