"""settings/guildsettings.py - Guild-wide settings class."""
# pylint: disable=too-few-public-methods

import datetime
from enum import Enum

from umongo import Document, EmbeddedDocument, fields

from inconnu.database import instance


class ExpPerms(str, Enum):
    """An enum for experience adjustment permissions."""

    UNRESTRICTED = "unrestricted"
    UNSPENT_ONLY = "unspent_only"
    LIFETIME_ONLY = "lifetime_only"
    ADMIN_ONLY = "admin_only"


@instance.register
class _GuildSettings(EmbeddedDocument):
    """Guild-wide settings."""

    accessibility = fields.BoolField(default=False)
    experience_permissions = fields.StrField(default=ExpPerms.UNRESTRICTED.value)
    oblivion_stains = fields.ListField(fields.IntField(), default=[1, 10])
    update_channel = fields.IntField(default=None)


@instance.register
class Guild(Document):
    """A simple container that represents a guild and its settings."""

    guild = fields.IntField(required=True)
    name = fields.StrField(required=True)
    active = fields.BoolField(default=True)
    joined = fields.DateTimeField(default=datetime.datetime.utcnow)
    left = fields.DateTimeField(default=None)

    settings = fields.EmbeddedField(_GuildSettings, default=_GuildSettings)

    class Meta:
        collection_name = "guilds"
