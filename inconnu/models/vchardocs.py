"""Sub-documents used in VChars."""
# pylint: disable=abstract-method, too-few-public-methods

import itertools
from datetime import UTC, datetime
from enum import StrEnum
from types import SimpleNamespace as SN
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field

import inconnu


class VCharProfile(BaseModel):
    """Maintains character biographical info."""

    biography: str = ""
    description: str = ""
    images: list[str] = Field(default_factory=list)


class VCharHeader(BaseModel):
    """Information for the /header command."""

    blush: int = Field(default=0)
    location: str = ""
    merits: str = ""
    flaws: str = ""
    temp: str = ""


class VCharExperienceEntry(BaseModel):
    """An experience log entry."""

    event: str
    amount: int
    reason: str
    admin: int
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VCharExperience(BaseModel):
    """Current and lifetime experience."""

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    unspent: int = Field(default=0, alias="current")
    lifetime: int = Field(default=0, alias="total")
    log: list[VCharExperienceEntry] = Field(default_factory=list)


class VCharMacro(BaseModel):
    """A roll macro."""

    name: str
    pool: list[str]
    hunger: bool
    difficulty: int
    rouses: int
    reroll_rouses: bool
    staining: str
    hunt: bool
    comment: Optional[str]


class VCharTrait(BaseModel):
    """A character trait, which may be an attribute, skill, Discipline, or custom.
    They're called specialties because I'm too lazy to rename them to subtraits."""

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    DELIMITER: ClassVar[str] = "."

    class Type(StrEnum):
        """The type of trait."""

        ATTRIBUTE = "attribute"
        CUSTOM = "custom"
        DISCIPLINE = "discipline"
        INHERENT = "inherent"
        SKILL = "skill"

    # Trait fields
    name: str
    rating: int
    type: str
    raw_subtraits: list[str] = Field(default_factory=list, alias="subtraits")

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
        return len(self.raw_subtraits) > 0

    @property
    def specialties(self) -> list[str]:
        """The trait's specialties."""
        return self.raw_subtraits.copy()

    def add_powers(self, powers: str | list[str]):
        """Add powers to the Discipline."""
        if not self.is_discipline:
            raise inconnu.errors.SpecialtiesNotAllowed("Only Disciplines may have powers.")

        self._add_subtraits(powers)

    def add_specialties(self, specialties: str | list[str]):
        """Add specialties to the trait."""
        if not self.specialties_allowed:
            raise inconnu.errors.SpecialtiesNotAllowed(
                "Only skills and custom traits may have specialties."
            )
        self._add_subtraits(specialties)

    def _add_subtraits(self, specialties: str | list[str] | set[str]):
        """Add a specialty or a power."""
        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        for specialty in specialties:
            if specialty.lower() not in map(str.lower, self.raw_subtraits):
                self.raw_subtraits.append(specialty)

        self.raw_subtraits.sort()

    def remove_specialties(self, specialties: str | list[str] | set[str]):
        """Remove specialties from the trait."""
        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        for specialty in map(str.lower, specialties):
            current = [spec.lower() for spec in self.raw_subtraits]
            try:
                index = current.index(specialty)
                del self.raw_subtraits[index]
            except ValueError:
                continue

    def matching(self, identifier: str, exact: bool) -> list[SN]:
        """Returns the fully qualified name if a string matches, or None."""
        matches = []
        if groups := self.expanding(identifier, exact, False):
            # The expanded values are sorted alphabetically, and we need
            # that to match our input for testing exactness
            tokens = identifier.split(VCharTrait.DELIMITER)
            tokens = [tokens[0]] + sorted(tokens[1:])
            normalized = VCharTrait.DELIMITER.join(tokens).lower()

            for expanded in groups:
                full_name = self.name
                if expanded[1:]:
                    # Add the specialties
                    full_name += f" ({', '.join(expanded[1:])})"

                key = VCharTrait.DELIMITER.join(expanded)
                rating = self.rating
                if not self.is_discipline:
                    rating += len(expanded[1:])

                matches.append(
                    SN(
                        name=full_name,
                        rating=rating,
                        exact=normalized == key.lower(),
                        key=key,
                        type=self.type,
                        discipline=self.is_discipline,
                    )
                )
        return matches

    def expanding(self, identifier: str, exact: bool, join=True) -> list[str | list[str]]:
        """Expand the user's input to full skill:spec names. If join is False, return a list."""
        tokens = [token.lower() for token in identifier.split(VCharTrait.DELIMITER)]

        # The comparison function takes a token and an instance var
        if exact:

            def comp(t: str, i: str) -> bool:
                return t == i.lower()
        else:

            def comp(t: str, i: str) -> bool:
                return i.lower().startswith(t)

        if comp(tokens[0], self.name):
            # A token might match multiple specs in the same skill. Therefore,
            # we need to make a list of all matching specs. We don't need to
            # track ratings, however, as we can just sum the spec counts at the
            # end.
            spec_groups = []
            for token in tokens[1:]:
                found_specs = []
                for specialty in self.raw_subtraits:
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

                seen_groups = set()
                for group in spec_groups:
                    if isinstance(group, str):
                        group = [group]
                    if len(set(group)) < len(group):
                        # Don't add groups with duplicate elements
                        continue

                    group = frozenset(group)
                    if group in seen_groups:
                        # Prevent (A, B) and (B, A) from both showing in the results
                        continue

                    seen_groups.add(group)
                    matches.append([self.name] + sorted(group))
            else:
                matches = [[self.name]]

            if join:
                return [VCharTrait.DELIMITER.join(match) for match in matches]
            return matches

        # No matches
        return []
