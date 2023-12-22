"""Custom user settings."""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed, SaveChanges, before_event
from pydantic import BaseModel, Field


class VUserSettings(BaseModel):
    """Represents individual user settings."""

    accessibility: bool = Field(default=False)
    last_modified: Optional[datetime] = None


class VUser(Document):
    """Represents a user and their settings."""

    user: Indexed(int, unique=True)
    settings: VUserSettings = Field(default_factory=VUserSettings)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @before_event(SaveChanges)
    def update_modification_date(self):
        """Update the settings modification date."""
        self.settings.last_modified = datetime.utcnow()

    class Settings:
        name = "users"
        use_state_management = True
