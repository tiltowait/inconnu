"""Sub-documents used in VChars."""
# pylint: disable=abstract-method, too-few-public-methods

from datetime import datetime

from umongo import EmbeddedDocument, fields

import inconnu


@inconnu.db.instance.register
class VCharProfile(EmbeddedDocument):
    """Maintains character biographical info."""

    biography: str = fields.StrField(default=str)
    description: str = fields.StrField(default=str)
    images: list[str] = fields.ListField(fields.StrField, default=list)


@inconnu.db.instance.register
class VCharHeader(EmbeddedDocument):
    """Information for the /header command."""

    blush: int = fields.IntField(default=0)
    location: str = fields.StrField(default=str)
    merits: str = fields.StrField(default=str)
    flaws: str = fields.StrField(default=str)
    temp: str = fields.StrField(default=str)


@inconnu.db.instance.register
class VCharExperienceEntry(EmbeddedDocument):
    """An experience log entry."""

    event: str = fields.StrField()
    amount: int = fields.IntField()
    reason: str = fields.StrField()
    admin: int = fields.IntField()
    date: datetime = fields.DateTimeField(default=datetime.utcnow)


@inconnu.db.instance.register
class VCharExperience(EmbeddedDocument):
    """Current and lifetime experience."""

    unspent: int = fields.IntField(default=0, attribute="current")
    lifetime: int = fields.IntField(default=0, attribute="total")
    log: list[VCharExperienceEntry] = fields.ListField(
        fields.EmbeddedField(VCharExperienceEntry), default=list
    )


@inconnu.db.instance.register
class VCharMacro(EmbeddedDocument):
    """A roll macro."""

    name: str = fields.StrField()
    pool: list[str] = fields.ListField(fields.StrField)
    hunger: bool = fields.BoolField()
    difficulty: int = fields.IntField()
    rouses: int = fields.IntField()
    reroll_rouses: bool = fields.BoolField()
    staining: str = fields.StrField()
    hunt: bool = fields.BoolField()
    comment: str = fields.StrField(allow_none=True, required=True)
