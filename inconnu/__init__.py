"""Primary Inconnu import."""

from typing import overload

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
    roleplay,
    settings,
    specialties,
    stats,
    tasks,
    traits,
    utils,
    views,
    webhookcache,
)
from inconnu.emoji import emojis
from inconnu.models import CharacterManager
from inconnu.roll import Roll

__all__ = (
    "bot",
    "char_mgr",
    "character",
    "CharacterManager",
    "d10",
    "db",
    "emojis",
    "errors",
    "experience",
    "fence",
    "get_avatar",
    "get_message",
    "header",
    "log",
    "macros",
    "misc",
    "models",
    "options",
    "post_url",
    "profile_url",
    "random",
    "reference",
    "Roll",
    "roleplay",
    "settings",
    "specialties",
    "stats",
    "tasks",
    "traits",
    "utils",
    "views",
    "webhookcache",
)

char_mgr = CharacterManager()
settings = settings.Settings()
bot = None

_rng = default_rng()


@overload
def d10(count: None = None) -> int:
    pass


@overload
def d10(count: int) -> list[int]:
    pass


def d10(count: int | None = None) -> list[int] | int:
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


def post_url(post_id: str) -> str:
    """Generate a post history URL."""
    return config.PROFILE_SITE + f"post/{post_id}"
