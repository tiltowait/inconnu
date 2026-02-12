"""Character wizard cache and related models."""

from typing import Optional, Self

import discord
import petname
from cachetools import TTLCache
from loguru import logger
from pydantic import BaseModel

import services
from services.guildcache import CachedGuild


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
            guild = await services.guild_cache.fetchguild(id)
            if guild is None:
                # This can probably never happen, but the return type hints
                # are wrong
                return cls.unknown(id)
            return cls.create(guild)
        except Exception:
            return cls.unknown(id)

    @classmethod
    def create(cls, guild: CachedGuild | discord.Guild) -> Self:
        """Create from a real Discord guild object."""
        if isinstance(guild, discord.Guild):
            icon = guild.icon.url if guild.icon else None
        else:
            icon = guild.icon
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

    def __init__(self, maxsize=1000, ttl=1800):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = TTLCache[str, WizardData](maxsize=maxsize, ttl=ttl)
        self.users = TTLCache[tuple[int, int], str](maxsize=maxsize, ttl=ttl)
        logger.info("Wizard Cache initialized. maxsize={}, ttl={}.", maxsize, ttl)

    @property
    def count(self) -> int:
        """The number of active wizards."""
        return len(self.cache)

    def register(self, guild: discord.Guild, user: int, spc: bool) -> str:
        """Register a character creation wizard."""
        cache_key = (guild.id, user)
        if cache_key in self.users:
            existing_token = self.users[cache_key]
            existing_wizard = self.get(existing_token)
            # If wizard still exists and spc flag matches, return existing token
            if existing_wizard and existing_wizard.spc == spc:
                return existing_token

        request = WizardData(guild=CharacterGuild.create(guild), user=user, spc=spc)
        key = petname.Generate(3)
        if not isinstance(key, str):
            raise ValueError("Unable to generate key")

        self.cache[key] = request
        self.users[cache_key] = key
        return key

    def get(self, key: str) -> WizardData | None:
        """Get the wizard request data off the cache (nondestructive)."""
        return self.cache.get(key)

    def delete(self, key: str):
        """Delete a wizard request."""
        wizard = self.get(key)
        if wizard is not None:
            del self.cache[key]
            cache_key = (int(wizard.guild.id), wizard.user)
            if cache_key in self.users:
                del self.users[cache_key]
