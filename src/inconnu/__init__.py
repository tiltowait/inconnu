"""Primary Inconnu import."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import InconnuBot
from inconnu import (
    character,
    constants,
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
    vr,
)
from inconnu.dice import d10, random
from inconnu.emoji import emojis
from inconnu.roll import Roll
from inconnu.settings import menu
from inconnu.urls import post_url, profile_url
from services import CharacterManager

__all__ = (
    "bot",
    "char_mgr",
    "character",
    "constants",
    "d10",
    "menu",
    "emojis",
    "experience",
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
    "vr",
)

char_mgr = CharacterManager()
bot: "InconnuBot"  # Assigned in bot.py
