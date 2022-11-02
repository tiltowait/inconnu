"""An RP post."""

from datetime import datetime

from umongo import Document, fields

import inconnu
from inconnu.models.rpheader import HeaderSubdoc


@inconnu.db.instance.register
class RPPost(Document):
    """Represents an RP post with the ability to maintain deltas."""

    date = fields.DateTimeField(default=datetime.utcnow)
    guild = fields.IntField()
    user = fields.IntField()
    message_id = fields.IntField()
    charid = fields.ObjectIdField()

    # The character's name when the post was made. We use this instead of the
    # current name (if it's changed), because the post will necessarily
    # reference the old name. It also has the added benefit of reducing
    # complexity; we don't have to look up the character by ID, nor do we
    # have to perform an update_many when a character is renamed.
    char_name = fields.StrField()  # This is used in case the character is deleted

    header = fields.EmbeddedField(HeaderSubdoc)
    content = fields.StrField()
    history = fields.ListField(fields.StrField, default=list)
    url = fields.UrlField(allow_none=True)

    class Meta:
        collection_name = "rp_posts"

    @classmethod
    def create(cls, character: "VChar", header: HeaderSubdoc, content: str, message: "Message"):
        """Create an RP post."""
        return cls(
            guild=character.guild,
            user=character.user,
            message_id=message.id,
            charid=character.pk,
            char_name=character.name,
            header=header,
            content=content,
            url=message.jump_url,
        )

    def edit_post(self, new_post: str):
        """Update the post content, if necessary."""
        if new_post != self.content:
            # We only bother with this if the post was actually changed
            self.history.insert(0, self.content)
            self.content = new_post