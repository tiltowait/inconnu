"""Character wizard cache and related models."""

from typing import Optional, Self

import discord
import petname
from cachetools import TTLCache
from loguru import logger
from pydantic import BaseModel

import inconnu


class CharacterGuild(BaseModel):
    """Guild data for the character endpoints."""

    id: str
    name: str
    icon: Optional[str]

    @classmethod
    async def fetch(cls, id: int) -> Self:
        """Fetch guild data from Discord."""
        try:
            # This method raises, despite the docs' indication otherwise, so we
            # have to wrap it in a try, irkshome though that is.
            guild = await inconnu.bot.get_or_fetch_guild(id)
            if guild is None:
                # This can probably never happen, but the return type hints
                # are wrong
                return cls.unknown(id)
            return cls.create(guild)
        except Exception:
            return cls.unknown(id)

    @classmethod
    def create(cls, guild: discord.Guild) -> Self:
        """Create from a real Discord guild object."""
        icon = guild.icon.url if guild.icon else None
        return cls(id=str(guild.id), name=guild.name, icon=icon)

    @classmethod
    def unknown(cls, id: int) -> Self:
        """Return generic data."""
        return cls(id=str(id), name="Unknown", icon=None)


class WizardData(BaseModel):
    """User character wizard request data."""

    spc: bool
    guild: CharacterGuild
    user: int


class WizardCache:
    """Maintains a TTL cache for character wizards."""

    def __init__(self, maxsize=1000, ttl=1200):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = TTLCache[str, WizardData](maxsize=maxsize, ttl=ttl)
        logger.info("Wizard Cache initialized. maxsize={}, ttl={}.", maxsize, ttl)

    def register(self, guild: discord.Guild, user: int, spc: bool) -> str:
        """Register a character creation wizard."""
        request = WizardData(guild=CharacterGuild.create(guild), user=user, spc=spc)
        key = petname.Generate(3)
        if not isinstance(key, str):
            raise ValueError("Unable to generate key")

        self.cache[key] = request
        return key

    def get(self, key: str) -> WizardData | None:
        """Get the wizard request data off the cache (nondestructive)."""
        return self.cache.get(key)

    def pop(self, key: str) -> WizardData | None:
        """Pop the wizard request data off the cache (destructive)."""
        if key not in self.cache:
            return None
        return self.cache.pop(key)
