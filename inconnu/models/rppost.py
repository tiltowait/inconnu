"""Rolepost models."""

from datetime import datetime, timezone

import discord
from umongo import Document, EmbeddedDocument, fields

import inconnu
from inconnu.models.rpheader import HeaderSubdoc


@inconnu.db.instance.register
class PostHistoryEntry(EmbeddedDocument):
    """Represents historic post content and a date of modification."""

    date = fields.DateTimeField()
    content = fields.StrField()


@inconnu.db.instance.register
class RPPost(Document):
    """Represents a Rolepost with the ability to maintain deltas."""

    # Metadata
    date = fields.DateTimeField(default=datetime.utcnow)
    date_modified = fields.DateTimeField(default=None)
    guild = fields.IntField()
    channel = fields.IntField()
    user = fields.IntField()
    message_id = fields.IntField()
    url = fields.UrlField(allow_none=True)
    deleted = fields.BoolField(default=False)
    deletion_date = fields.DateTimeField(default=None)
    id_chain = fields.ListField(fields.IntField, default=list)

    # Content
    header = fields.EmbeddedField(HeaderSubdoc)
    content = fields.StrField()
    mentions = fields.ListField(fields.IntField, default=list)
    history = fields.ListField(fields.EmbeddedField(PostHistoryEntry), default=list)

    # Custom
    title = fields.StrField(default=None)
    tags = fields.ListField(fields.StrField, default=list)

    @property
    def utc_date(self) -> datetime:
        """The UTC-aware post date."""
        return self.date.replace(tzinfo=timezone.utc)

    class Meta:
        collection_name = "rp_posts"

    @classmethod
    def create(
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
