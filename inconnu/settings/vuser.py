"""Custom user settings."""

from beanie import Document
from pydantic import BaseModel, Field


class VUserSettings(BaseModel):
    """Represents individual user settings."""

    accessibility: bool = False


class VUser(Document):
    """Represents a user and their settings."""

    user: int
    settings: VUserSettings = Field(default_factory=VUserSettings)

    class Settings:
        name = "users"
