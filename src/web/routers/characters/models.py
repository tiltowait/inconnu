"""Pydantic models for character API endpoints."""

from typing import Optional, Self

import discord
from pydantic import BaseModel

import inconnu
from models import VChar


class CharacterGuild(BaseModel):
    """Guild data for the character endpoints."""

    id: int
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
        return cls(id=guild.id, name=guild.name, icon=icon)

    @classmethod
    def unknown(cls, id: int) -> Self:
        """Return generic data."""
        return cls(id=id, name="Unknown", icon=None)


class AuthorizedCharacter(BaseModel):
    """The character data for /characters/{oid}."""

    guild: CharacterGuild
    character: VChar


class AuthorizedCharacterList(BaseModel):
    """The character data for /characters."""

    guilds: list[CharacterGuild]
    characters: list[VChar]
