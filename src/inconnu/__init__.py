"""Primary Inconnu import."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import InconnuBot
from inconnu import (
    character,
    experience,
    header,
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

__all__ = (
    "bot",
    "character",
    "d10",
    "menu",
    "emojis",
    "experience",
    "header",
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

bot: "InconnuBot"  # Assigned in bot.py
