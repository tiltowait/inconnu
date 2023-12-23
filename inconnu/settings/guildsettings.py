"""settings/guildsettings.py - Guild-wide settings class."""

from datetime import datetime
from enum import Enum
from typing import Optional

import discord
from beanie import Document, Indexed, SaveChanges, before_event
from pydantic import BaseModel, Field


class ExpPerms(str, Enum):
    """An enum for experience adjustment permissions."""

    UNRESTRICTED = "unrestricted"
    UNSPENT_ONLY = "unspent_only"
    LIFETIME_ONLY = "lifetime_only"
    ADMIN_ONLY = "admin_only"


class VGuildSettings(BaseModel):
    accessibility: bool = False
    oblivion_stains: list[int] = [1, 10]  # Safe and tested
    add_empty_resonance: bool = False
    max_hunger: int = 5
    experience_permissions: ExpPerms = ExpPerms.UNRESTRICTED
    update_channel: Optional[int] = None
    changelog_channel: Optional[int] = None
    deletion_channel: Optional[int] = None


class VGuild(Document):
    """A guild record containing guild settings and some basic parameters."""

    guild: Indexed(int, unique=True)
    name: str
    active: bool = True
    joined: datetime = Field(default_factory=datetime.utcnow)
    left: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    settings: VGuildSettings = Field(default_factory=VGuildSettings)

    @classmethod
    def from_guild(cls, guild: discord.Guild) -> "VGuild":
        """Generate a VGuild from a discord.Guild."""
        return VGuild(guild=guild.id, name=guild.name)

    @before_event(SaveChanges)
    def update_modification_date(self):
        """Update the last_modified field."""
        self.last_modified = datetime.utcnow()

    class Settings:
        name = "guilds"
        use_state_management = True
