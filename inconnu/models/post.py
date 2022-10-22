"""An RP post."""

from datetime import datetime

from umongo import Document, fields

import inconnu


@inconnu.db.instance.register
class RPPost(Document):
    """Represents an RP post with the ability to maintain deltas."""

    guild = fields.IntField()
    user = fields.IntField()
    charid = fields.ObjectIdField()
    date = fields.DateTimeField(default=datetime.utcnow)

    content = fields.StrField()
    history = fields.ListField(fields.StrField, default=list)

    class Meta:
        collection_name = "rp_posts"

    @classmethod
    def create(cls, character: "VChar", content: str):
        """Create an RP post."""
        return cls(guild=character.guild, user=character.user, charid=character.pk, content=content)

    def edit_post(self, new_post: str):
        """Update the post content, if necessary."""
        if new_post != self.content:
            # We only bother with this if the post was actually changed
            self.history.insert(0, self.content)
            self.content = new_post
