"""Rolepost models."""

from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Optional

import discord
from beanie import Document
from pydantic import AnyUrl, BaseModel, Field

from models.rpheader import HeaderSubdoc

if TYPE_CHECKING:
    from models import VChar


class PostHistoryEntry(BaseModel):
    """Represents historic post content and a date of modification."""

    date: datetime
    content: str


class RPPost(Document):
    """Represents a Rolepost with the ability to maintain deltas."""

    # Metadata
    date: datetime = Field(default_factory=datetime.utcnow)
    date_modified: Optional[datetime] = None
    guild: int
    channel: int
    user: int
    message_id: int
    url: Optional[AnyUrl]
    deleted: bool = False
    deletion_date: Optional[datetime] = None
    id_chain: list[int] = Field(default_factory=list)

    # Content
    header: HeaderSubdoc
    content: str
    mentions: list[int] = Field(default_factory=list)
    history: list[PostHistoryEntry] = Field(default_factory=list)

    # Custom
    title: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @property
    def utc_date(self) -> datetime:
        """The UTC-aware post date."""
        return self.date.replace(tzinfo=timezone.utc)

    class Settings:
        name = "rp_posts"
        use_state_management = True
        validate_on_save = True

    @classmethod
    def new(
        cls,
        *,
        interaction: discord.Interaction,
        character: "VChar",
        header: HeaderSubdoc,
        content: str,
        message: discord.Message,
        mentions: list[int],
        title: str | None,
        tags: list[str],
    ):
        """Create a Rolepost."""
        if interaction.channel_id is None:
            raise ValueError("Interaction channel has no ID")
        if interaction.user is None:
            raise ValueError("Interaction user does not exist")

        return cls(
            guild=character.guild,
            channel=interaction.channel_id,
            user=interaction.user.id,
            message_id=message.id,
            header=header,
            content=content,
            url=AnyUrl(message.jump_url),
            mentions=mentions,
            title=title,
            tags=tags,
        )

    def edit_post(self, new_post: str):
        """Update the post content, if necessary."""
        if new_post != self.content:
            # We only bother with this if the post was actually changed
            entry = PostHistoryEntry(
                date=self.date_modified or self.date,
                content=self.content,
            )
            self.history.insert(0, entry)
            self.content = new_post
            self.date_modified = datetime.now(UTC)
