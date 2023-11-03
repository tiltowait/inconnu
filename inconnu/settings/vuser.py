"""Custom user settings."""

from umongo import Document, EmbeddedDocument, fields

import inconnu


@inconnu.db.instance.register
class VUserSettings(EmbeddedDocument):
    """Represents individual user settings."""

    accessibility = fields.BoolField(default=False)


@inconnu.db.instance.register
class VUser(Document):
    """Represents a user and their settings."""

    user = fields.IntField(required=True)
    settings = fields.EmbeddedField(VUserSettings, default=VUserSettings)
