"""An RP post."""

from datetime import datetime

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
    """Represents an RP post with the ability to maintain deltas."""

    # Metadata
    date = fields.DateTimeField(default=datetime.utcnow)
    date_modified = fields.DateTimeField(default=None)
    guild = fields.IntField()
    channel = fields.IntField()
    user = fields.IntField()
    message_id = fields.IntField()
    url = fields.UrlField(allow_none=True)
    deleted = fields.BoolField(default=False)
    id_chain = fields.ListField(fields.IntField, default=list)

    # Content
    header = fields.EmbeddedField(HeaderSubdoc)
    content = fields.StrField()
    history = fields.ListField(fields.EmbeddedField(PostHistoryEntry), default=list)

    class Meta:
        collection_name = "rp_posts"

    @classmethod
    def create(
        cls,
        channel: int,
        character: "VChar",
        header: HeaderSubdoc,
        content: str,
        message: "Message",
    ):
        """Create an RP post."""
        return cls(
            guild=character.guild,
            channel=channel,
            user=character.user,
            message_id=message.id,
            header=header,
            content=content,
            url=message.jump_url,
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
