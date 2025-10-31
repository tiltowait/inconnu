"""Primary Inconnu import."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import InconnuBot
from inconnu import (
    character,
    common,
    constants,
    db,
    embeds,
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
    vr,
    webhookcache,
)
from inconnu.dice import d10, random
from inconnu.emoji import emojis
from inconnu.models import CharacterManager
from inconnu.roll import Roll
from inconnu.settings import VUser
from inconnu.urls import post_url, profile_url
from inconnu.utils import fence, get_avatar, get_message

__all__ = (
    "bot",
    "char_mgr",
    "character",
    "CharacterManager",
    "common",
    "constants",
    "d10",
    "db",
    "emojis",
    "embeds",
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
    "vr",
    "VUser",
    "webhookcache",
)

char_mgr = CharacterManager()
settings = settings.Settings()
bot: "InconnuBot"  # Assigned in bot.py
