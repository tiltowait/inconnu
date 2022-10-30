"""Header subdoc."""

import copy

from umongo import EmbeddedDocument, fields

import inconnu


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

    hp_damage = fields.StrField()
    wp_damage = fields.StrField()

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
            hp_damage=track_damage(character.superficial_hp, character.aggravated_hp),
            wp_damage=track_damage(character.superficial_wp, character.aggravated_wp),
        )
        return header_doc


def track_damage(sup: int, agg: int) -> str:
    """Generate a text value for the tracker damage."""
    # We want to keep the total HP/WP secret. Instead, just show damage
    damage = []
    if sup > 0:
        damage.append(f"-{sup}s")
    if agg > 0:
        damage.append(f"-{agg}a")

    if damage:
        return "/".join(damage)
    return "-0"
