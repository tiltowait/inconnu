"""Custom user settings."""

from async_lru import alru_cache
from beanie import Document
from pydantic import BaseModel, Field


class VUserSettings(BaseModel):
    """Represents individual user settings."""

    accessibility: bool = False

    @property
    def use_emojis(self) -> bool:
        """Whether to use emojis. Inverse of accessibility."""
        return not self.accessibility


class VUser(Document):
    """Represents a user and their settings."""

    user: int
    settings: VUserSettings = Field(default_factory=VUserSettings)

    @classmethod
    @alru_cache(maxsize=1024)
    async def get_or_fetch(cls, id: int) -> "VUser":
        """Return a cached VUser, fetch it from the database, or create a new one."""
        vuser = await VUser.find_one({"user": id})
        if vuser is None:
            vuser = cls(user=id)
        return vuser

    class Settings:
        name = "users"
        use_state_management = True
        validate_on_save = True
