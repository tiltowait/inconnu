"""Header subdoc."""

import copy
from typing import TYPE_CHECKING

from bson import ObjectId
from umongo import EmbeddedDocument, fields

import inconnu

if TYPE_CHECKING:
    from inconnu.models import VChar


@inconnu.db.instance.register
class DamageSubdoc(EmbeddedDocument):
    """Tracks aggravated and superficial damage."""

    superficial = fields.IntField()
    aggravated = fields.IntField()


@inconnu.db.instance.register
class HeaderSubdoc(EmbeddedDocument):
    """A subdocument for RP headers. It gets stored in the database for later editing.."""

    MAX_TITLE_LEN = 256

    charid: ObjectId = fields.ObjectIdField()
    char_name: str = fields.StrField()

    blush: int = fields.IntField()
    hunger: int = fields.IntField(allow_none=True)
    location: str = fields.StrField()
    merits: str = fields.StrField()
    flaws: str = fields.StrField()
    temp: str = fields.StrField()

    health = fields.EmbeddedField(DamageSubdoc)
    willpower = fields.EmbeddedField(DamageSubdoc)

    @property
    def blush_str(self) -> str | None:
        """The Blush string, if applicable."""
        if self.blush == -1:
            return None
        return "Blushed" if self.blush else "Not Blushed"

    @property
    def base_title(self) -> str:
        """Header title: Location and blush status."""
        title_fields = [self.location, self.blush_str]
        base = " • ".join(filter(lambda f: f, title_fields))

        return base[: HeaderSubdoc.MAX_TITLE_LEN]

    @property
    def title(self) -> str:
        """Make a header title out of the given fields."""
        full = f"{self.char_name} • {self.base_title}"
        return full[: HeaderSubdoc.MAX_TITLE_LEN]

    @classmethod
    def create(cls, character: "VChar", **kwargs):
        """Prepare the header with any overrides."""
        header = copy.deepcopy(character.header)

        if kwargs["blush"] is not None:
            header.blush = kwargs["blush"]
        header.location = kwargs["location"] or header.location
        header.merits = kwargs["merits"] or header.merits
        header.flaws = kwargs["flaws"] or header.flaws
        header.temp = kwargs["temp"] or header.temp

        if character.is_vampire:
            hunger = kwargs.pop("hunger") or character.hunger
        else:
            hunger = None

        header_doc = cls(
            charid=character.pk,
            char_name=character.name,
            blush=header.blush,
            hunger=hunger,
            location=header.location,
            merits=header.merits,
            flaws=header.flaws,
            temp=header.temp,
            health=DamageSubdoc(
                superficial=character.superficial_hp, aggravated=character.aggravated_hp
            ),
            willpower=DamageSubdoc(
                superficial=character.superficial_wp, aggravated=character.aggravated_wp
            ),
        )
        return header_doc
