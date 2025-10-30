"""Primary Inconnu import."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import InconnuBot
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
from inconnu.dice import d10, random
from inconnu.emoji import emojis
from inconnu.models import CharacterManager
from inconnu.roll import Roll
from inconnu.urls import post_url, profile_url
from inconnu.utils import fence, get_avatar, get_message

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
bot: "InconnuBot"  # Assigned in bot.py
