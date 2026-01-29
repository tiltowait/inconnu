"""Primary Inconnu import."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import InconnuBot
from inconnu import (
    character,
    common,
    constants,
    embeds,
    experience,
    header,
    log,
    macros,
    misc,
    options,
    reference,
    roleplay,
    settings,
    specialties,
    stats,
    traits,
    utils,
    views,
    vr,
)
from caches import CharacterManager
from inconnu.dice import d10, random
from inconnu.emoji import emojis
from inconnu.roll import Roll
from inconnu.settings import menu
from inconnu.urls import post_url, profile_url
from inconnu.utils import fence, get_avatar, get_message

__all__ = (
    "bot",
    "char_mgr",
    "character",
    "common",
    "constants",
    "d10",
    "menu",
    "emojis",
    "embeds",
    "experience",
    "fence",
    "get_avatar",
    "get_message",
    "header",
    "log",
    "macros",
    "misc",
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
    "traits",
    "utils",
    "views",
    "vr",
)

char_mgr = CharacterManager()
bot: "InconnuBot"  # Assigned in bot.py
