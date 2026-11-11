"""Read-only integration contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Outcome = Literal["critical", "messy", "success", "fail", "total_fail", "bestial"]


class KeyRequest(BaseModel):
    """Channel-scoped key creation settings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64, strict=True)
    guild_id: str = Field(pattern=r"^[1-9][0-9]{0,19}$", strict=True)
    channel_id: str = Field(pattern=r"^[1-9][0-9]{0,19}$", strict=True)
    expires_in_days: int | None = Field(default=90, ge=1, le=90, strict=True)
    creation_id: UUID | None = None

    @field_validator("guild_id", "channel_id")
    @classmethod
    def snowflake(cls, value: str) -> str:
        """Reject IDs outside Discord's unsigned integer range."""
        if int(value) >= 2**64:
            raise ValueError("Invalid Discord ID")
        return value


class KeySummary(BaseModel):
    """Key metadata that never includes its credential digest or secret."""

    id: str
    name: str
    prefix: str
    guild_id: str
    channel_id: str
    scope: Literal["rolls:read"] = "rolls:read"
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


class ChannelChoice(BaseModel):
    """An eligible channel displayed in the account's key form."""

    guild_id: str
    guild_name: str
    channel_id: str
    channel_name: str


class KeyList(BaseModel):
    """Owned keys and channels available to the account."""

    keys: list[KeySummary]
    channels: list[ChannelChoice]


class CreatedKey(BaseModel):
    """A newly created key with its one-time secret."""

    key: KeySummary
    secret: str


class RevokedKey(BaseModel):
    """Metadata returned after revoking an owned key."""

    key: KeySummary


class RollSummary(BaseModel):
    """The public allowlist of one stored roll's outcomes."""

    id: str
    created_at: datetime
    character_id: str | None
    owner_id: str
    original_outcome: Outcome
    final_outcome: Outcome
    rerolled: bool
    hidden: bool
    difficulty: int | None
    margin: int | None
    impaired: bool
    normal_dice: list[int]
    hunger_dice: list[int]
    reroll_strategy: str | None
    reroll_margin: int | None
    reroll_dice: list[int] | None


class RollPage(BaseModel):
    """A bounded page of channel rolls and its continuation cursor."""

    rolls: list[RollSummary]
    next_cursor: str | None
