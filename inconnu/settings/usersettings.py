"""settings/usersettings.py - User-specific settings."""
# pylint: disable=too-few-public-methods

from umongo import Document, EmbeddedDocument, fields

from inconnu.database import instance


@instance.register
class _UserSettings(EmbeddedDocument):
    """User-specific settings."""

    accessibility = fields.BoolField(default=False)


@instance.register
class User(Document):
    """Container for user settings."""

    user = fields.IntField(required=True)
    settings = fields.EmbeddedField(_UserSettings, default=_UserSettings)

    class Meta:
        collection_name = "users"
