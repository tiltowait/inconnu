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
from inconnu.roll import Roll
from inconnu.settings import menu

__all__ = (
    "Roll",
    "bot",
    "character",
    "d10",
    "experience",
    "header",
    "macros",
    "menu",
    "misc",
    "options",
    "random",
    "reference",
    "roleplay",
    "settings",
    "specialties",
    "stats",
    "traits",
    "vr",
)

bot: "InconnuBot"  # Assigned in bot.py
