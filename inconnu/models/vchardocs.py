"""Sub-documents used in VChars."""
# pylint: disable=abstract-method, too-few-public-methods

import itertools
from datetime import datetime
from enum import Enum
from types import SimpleNamespace as SN

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


@inconnu.db.instance.register
class VCharTrait(EmbeddedDocument):
    """A character trait, which may be an attribute, skill, Discipline, or custom."""

    class Type(str, Enum):
        """The type of trait."""

        ATTRIBUTE = "attribute"
        CUSTOM = "custom"
        DISCIPLINE = "discipline"
        INHERENT = "inherent"
        SKILL = "skill"

    # Trait fields
    name: str = fields.StrField(required=True)
    rating: int = fields.IntField(required=True)
    type: str = fields.StrField(required=True)
    _specialties: list[str] = fields.ListField(
        fields.StrField, default=list, attribute="specialties"
    )

    @property
    def is_attribute(self) -> bool:
        """Whether the trait is an attribute."""
        return self.type == VCharTrait.Type.ATTRIBUTE

    @property
    def is_custom(self) -> bool:
        """Whether the trait is custom."""
        return self.type == VCharTrait.Type.CUSTOM

    @property
    def is_discipline(self) -> bool:
        """Whether the trait is a Discipline."""
        return self.type == VCharTrait.Type.DISCIPLINE

    @property
    def is_inherent(self) -> bool:
        """Whether the trait is inherent."""
        return self.type == VCharTrait.Type.INHERENT

    @property
    def is_skill(self) -> bool:
        """Whether the trait is a skill."""
        return self.type == VCharTrait.Type.SKILL

    @property
    def specialties_allowed(self) -> bool:
        """Only skills and custom traits can have specialties."""
        return self.type in [VCharTrait.Type.CUSTOM.value, VCharTrait.Type.SKILL.value]

    @property
    def has_specialties(self) -> bool:
        """Whether the trait has any specialties."""
        return len(self._specialties) > 0

    @property
    def specialties(self) -> list[str]:
        """The trait's specialties."""
        return self._specialties.copy()

    def add_specialties(self, specialties: str | list[str]):
        """Add specialties to the trait."""
        if not self.specialties_allowed:
            raise inconnu.errors.SpecialtiesNotAllowed(
                "Only skills and custom traits may have specialties."
            )

        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        for specialty in specialties:
            if specialty.lower() not in map(str.lower, self._specialties):
                self._specialties.append(specialty)

        self._specialties.sort()

    def remove_specialties(self, specialties: str | list[str]):
        """Remove specialties from the trait."""
        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        for specialty in map(str.lower, specialties):
            current = [spec.lower() for spec in self._specialties]
            try:
                index = current.index(specialty)
                del self._specialties[index]
            except ValueError:
                continue

    def matching(self, identifier: str, exact: bool) -> list[SN]:
        """Returns the fully qualified name if a string matches, or None."""
        matches = []
        if groups := self.expanding(identifier, exact, False):
            # The expanded values are sorted alphabetically, and we need
            # that to match our input for testing exactness
            tokens = identifier.split(":")
            tokens = [tokens[0]] + sorted(tokens[1:])
            normalized = ":".join(tokens).lower()

            for expanded in groups:
                full_name = self.name
                if expanded[1:]:
                    # Add the specialties
                    full_name += f" ({', '.join(expanded[1:])})"

                key = ":".join(expanded)

                matches.append(
                    SN(
                        name=full_name,
                        rating=self.rating + len(expanded[1:]),
                        exact=normalized == key.lower(),
                        key=key,
                        type=self.type,
                    )
                )
        return matches

    def expanding(self, identifier: str, exact: bool, join=True) -> list[str | list[str]]:
        """Expand the user's input to full skill:spec names. If join is False, return a list."""
        tokens = [token.lower() for token in identifier.split(":")]

        # The "comp" lambda takes a token and an instance var
        if exact:
            comp = lambda t, i: t == i.lower()
        else:
            comp = lambda t, i: i.lower().startswith(t)

        if comp(tokens[0], self.name):
            # A token might match multiple specs in the same skill. Therefore,
            # we need to make a list of all matching specs. We don't need to
            # track ratings, however, as we can just sum the spec counts at the
            # end.
            spec_groups = []
            for token in tokens[1:]:
                found_specs = []
                for specialty in self._specialties:
                    if comp(token, specialty):
                        found_specs.append(specialty)
                spec_groups.append(found_specs)

            # If no specialties were given, then spec_groups is empty. If
            # specialties were given but not found, then we have [[]], which
            # will eventually return [].
            #
            # This also holds true if multiple specs are given and only one
            # fails to match (e.g. [["Kindred"], []]). It works because
            # itertools.product() will return an empty list if one of its
            # arguments is itself an empty list. Therefore, we don't need any
            # "if not group: return None" patterns in this next block.

            if spec_groups:
                matches = []
                if len(spec_groups) > 1:
                    # Multiple matching specs per token; get all combinations:
                    #     [[1, 2], [3]] -> [(1, 3), (2, 3)]
                    spec_groups = itertools.product(*spec_groups)
                else:
                    # Zero or one match; golden path
                    spec_groups = spec_groups[0]

                seen_groups = []
                for group in spec_groups:
                    if isinstance(group, str):
                        group = [group]
                    if len(set(group)) < len(group):
                        # This group has at least one duplicate spec; skip
                        continue

                    group = set(group)
                    if group in seen_groups:
                        # Prevent (A, B) and (B, A) from both showing in the results
                        continue

                    matches.append([self.name] + sorted(group))
            else:
                matches = [[self.name]]

            if join:
                return [":".join(match) for match in matches]
            return matches

        # No matches
        return []
