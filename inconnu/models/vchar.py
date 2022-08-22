"""Player-character model."""
# pylint: disable=missing-class-docstring, too-few-public-methods, abstract-method

from datetime import datetime

from umongo import Document, fields

import inconnu

from .vchardocs import VCharExperience, VCharHeader, VCharMacro, VCharProfile


@inconnu.db.instance.register
class VChar(Document):
    """A vampire, mortal, ghoul, or thin-blood character."""

    # Ownership
    guild: int = fields.IntField()
    user: int = fields.IntField()

    # Basic stats used in trackers
    name: str = fields.StrField()
    splat: str = fields.StrField()
    health: str = fields.StrField()
    willpower: str = fields.StrField()
    humanity: int = fields.IntField()
    stains: int = fields.IntField(default=0)
    hunger: int = fields.IntField(default=1)
    potency: int = fields.IntField()
    traits: dict[str, int] = fields.DictField()

    # Biographical/profile data
    profile: VCharProfile = fields.EmbeddedField(VCharProfile, default=VCharProfile)
    convictions: list[str] = fields.ListField(fields.StrField, default=list)
    header: VCharHeader = fields.EmbeddedField(VCharHeader, default=VCharHeader)

    # Misc/convenience
    macros: list[VCharMacro] = fields.ListField(fields.EmbeddedField(VCharMacro), default=list)
    experience: VCharExperience = fields.EmbeddedField(VCharExperience, default=VCharExperience)
    log: dict = fields.DictField(default=dict)

    class Meta:
        collection_name = "characters"

    def pre_insert(self):
        """Last-minute prep."""
        self.log["created"] = datetime.utcnow()

        if self.splat == "thinblood":
            self.splat = "thin-blood"
