"""Header subdoc."""

import copy

from umongo import EmbeddedDocument, fields

import inconnu


@inconnu.db.instance.register
class DamageSubdoc(EmbeddedDocument):
    """Tracks aggravated and superficial damage."""

    superficial = fields.IntField()
    aggravated = fields.IntField()


@inconnu.db.instance.register
class HeaderSubdoc(EmbeddedDocument):
    """A subdocument for RP headers. It gets stored in the database for later editing.."""

    MAX_TITLE_LEN = 256

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

    def gen_title(self, char_name: str) -> str:
        """Make a header title out of the given fields."""
        title_fields = [char_name, self.location, self.blush_str]
        title = " • ".join(filter(lambda f: f is not None, title_fields))

        return title[: HeaderSubdoc.MAX_TITLE_LEN]

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