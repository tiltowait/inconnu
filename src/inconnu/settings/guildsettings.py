"""settings/guildsettings.py - Guild-wide settings class."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from async_lru import alru_cache
from beanie import Document
from discord import Guild
from pydantic import BaseModel, Field


class ExpPerms(StrEnum):
    """An enum for experience adjustment permissions."""

    UNRESTRICTED = "unrestricted"
    UNSPENT_ONLY = "unspent_only"
    LIFETIME_ONLY = "lifetime_only"
    ADMIN_ONLY = "admin_only"


class VGuildSettings(BaseModel):
    """Represents an individual guild's settings."""

    accessibility: bool = False
    experience_permissions: ExpPerms = ExpPerms.UNRESTRICTED
    oblivion_stains: list[int] = Field(default_factory=lambda: [1, 10])
    update_channel: Optional[int] = None
    changelog_channel: Optional[int] = None
    deletion_channel: Optional[int] = None
    add_empty_resonance: bool = False
    max_hunger: int = Field(ge=5, le=10, default=5)

    @property
    def use_emojis(self) -> bool:
        """Whether to use emojis. Inverse of accessibility."""
        return not self.accessibility


class VGuild(Document):
    """Represents a guild and its settings."""

    guild: int
    name: str
    active: bool = True
    joined: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    left: Optional[datetime] = None
    settings: VGuildSettings = Field(default_factory=VGuildSettings)

    @classmethod
    @alru_cache(maxsize=1024)
    async def get_or_fetch(cls, guild: Guild | None) -> "VGuild":
        """Return a cached VGuild, fetch it from the database, or create a new one."""
        if guild is None:
            return VGuild(guild=0, name="DMs")

        vguild = await VGuild.find_one({"guild": guild.id})
        if vguild is None:
            vguild = cls(guild=guild.id, name=guild.name)
            await vguild.save()
        return vguild

    class Settings:
        name = "guilds"
        use_state_management = True
        validate_on_save = True
