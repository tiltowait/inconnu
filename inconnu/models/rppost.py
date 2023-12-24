"""Rolepost models."""

from datetime import datetime, timezone
from typing import Optional

import discord
from beanie import Document
from pydantic import BaseModel, Field, HttpUrl

from inconnu.models.rpheader import HeaderSubdoc
from inconnu.models.vchar import VChar


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
    url: Optional[HttpUrl]
    deleted: bool = False
    deletion_date: Optional[datetime] = None
    id_chain: list[int] = []

    # Content
    header: HeaderSubdoc
    content: str
    mentions: list[int] = []
    history: list[PostHistoryEntry] = []

    # Custom
    title: Optional[str] = None
    tags: list[str] = []

    @property
    def utc_date(self) -> datetime:
        """The UTC-aware post date."""
        return self.date.replace(tzinfo=timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        interaction: discord.Interaction,
        character: VChar,
        header: HeaderSubdoc,
        content: str,
        message: discord.Message,
        mentions: list[int],
        title: str | None,
        tags: list[str],
    ):
        """Create a Rolepost."""
        return cls(
            guild=character.guild,
            channel=interaction.channel_id,
            user=interaction.user.id,
            message_id=message.id,
            header=header,
            content=content,
            url=message.jump_url,
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
            self.date_modified = datetime.utcnow()

    class Settings:
        name = "rp_posts"
        use_state_management = True
