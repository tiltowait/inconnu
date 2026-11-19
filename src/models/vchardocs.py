"""Sub-documents used in VChars."""

from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from typing import ClassVar, Literal, NamedTuple, TypedDict, overload

from pydantic import BaseModel, ConfigDict, Field, computed_field

import errors

CAREER_STATS_LIVE = datetime(2026, 11, 14, 20, tzinfo=UTC)  # Noon PST
VICTIMS_DRAINED_LIVE = datetime(2026, 11, 18, 20, tzinfo=UTC)  # Noon PST

# The most specialty combinations matching keeps while expanding. Exact names
# narrow to one, so only vague input ("brawl....." on a trait with many
# specialties) reaches it; capping it keeps matching cheap
MAX_SUBTRAIT_MATCHES = 100


class BlushState(IntEnum):
    """A character's Blush of Life status."""

    NA = -1
    OFF = 0
    ON = 1


class VCharSplat(StrEnum):
    """Character splats."""

    VAMPIRE = "vampire"
    GHOUL = "ghoul"
    MORTAL = "mortal"
    THIN_BLOOD = "thin-blood"


class VCharProfile(BaseModel):
    """Maintains character biographical info."""

    biography: str = ""
    description: str = ""
    images: list[str] = Field(default_factory=list)


class VCharHeader(BaseModel):
    """Information for the /header command."""

    blush: BlushState = BlushState.OFF
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


class VCharLog(BaseModel):
    """When the character was created and its owner left, and running counts
    of gameplay events. Counts only go up.

    Some counters are stored under older, vaguer keys. Their aliases keep those
    keys in the database, while the API shows the clearer names."""

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    # When each counter started; older characters' counts are incomplete
    TRACKING_STARTED: ClassVar[dict[str, datetime]] = {
        "deepest_degeneration": CAREER_STATS_LIVE,
        "degenerations": CAREER_STATS_LIVE,
        "frenzy_resisted": CAREER_STATS_LIVE,
        "hunger_gained": CAREER_STATS_LIVE,
        "hunts": CAREER_STATS_LIVE,
        "num_victims_drained": VICTIMS_DRAINED_LIVE,
        "rouse_failures": CAREER_STATS_LIVE,
        "rouse_successes": CAREER_STATS_LIVE,
        "surges": CAREER_STATS_LIVE,
        "times_impaired": CAREER_STATS_LIVE,
        "times_mended": CAREER_STATS_LIVE,
        "times_slaked": CAREER_STATS_LIVE,
        "worst_health": CAREER_STATS_LIVE,
        "worst_willpower": CAREER_STATS_LIVE,
    }

    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    left: datetime | None = None  # The owner left the server; culled after 30 days

    deepest_degeneration: int = 0  # Most Stains ever beyond Humanity's empty boxes
    degenerations: int = 0  # Times entering degeneration
    frenzy_resisted: int = 0
    health_aggravated: int = 0
    health_superficial: int = 0
    hunger_gained: int = 0
    hunger_slaked: int = Field(default=0, alias="slake", serialization_alias="hunger_slaked")
    hunts: int = 0  # Hunt macros rolled
    num_victims_drained: int = 0  # Drain chosen in a hunt's Slake menu
    remorse_checks: int = Field(default=0, alias="remorse", serialization_alias="remorse_checks")
    remorse_failures: int = Field(default=0, alias="degen", serialization_alias="remorse_failures")
    rouse_checks: int = Field(default=0, alias="rouse", serialization_alias="rouse_checks")
    rouse_failures: int = 0
    rouse_successes: int = 0
    stains_gained: int = Field(default=0, alias="stains", serialization_alias="stains_gained")
    surges: int = 0
    times_awakened: int = Field(default=0, alias="awaken", serialization_alias="times_awakened")
    times_blushed: int = Field(default=0, alias="blush", serialization_alias="times_blushed")
    times_frenzied: int = Field(default=0, alias="frenzy", serialization_alias="times_frenzied")
    times_impaired: int = 0  # Times going from unimpaired to impaired
    times_mended: int = 0  # Superficial (/mend) and Aggravated (/aggheal) healing
    times_slaked: int = 0
    willpower_aggravated: int = 0
    willpower_superficial: int = 0
    worst_health: str = ""  # The Health track at its worst; see VChar.damage_severity()
    worst_willpower: str = ""  # Likewise for Willpower

    def record_rouse(self, successes: int, failures: int, hunger_gained: int):
        """Record a set of Rouse checks and the Hunger they caused."""
        self.rouse_checks += successes + failures
        self.rouse_successes += successes
        self.rouse_failures += failures
        self.hunger_gained += hunger_gained

    @computed_field
    @property
    def incomplete_since(self) -> dict[str, datetime]:
        """The counters that started after the character was created, so its
        counts are incomplete, and when they started."""
        # Dates loaded from the database are naive UTC
        created = self.created
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)

        return {field: date for field, date in self.TRACKING_STARTED.items() if created < date}

    @computed_field
    @property
    def remorse_successes(self) -> int:
        """Successful Remorse checks."""
        return self.remorse_checks - self.remorse_failures


class MacroUpdate(TypedDict, total=False):
    """Changes to a macro's fields."""

    name: str
    pool: list[str]
    hunger: bool
    difficulty: int
    rouses: int
    reroll_rouses: bool
    staining: str
    hunt: bool
    comment: str


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
    comment: str | None


class TraitMatch(NamedTuple):
    """A trait (and any specialties) matching a user's identifier."""

    name: str
    rating: int
    exact: bool
    key: str
    type: str
    discipline: bool


def _fold(name: str, ignore_spaces: bool) -> str:
    """Lowercase a name for comparison, removing its spaces if asked."""
    name = name.lower()
    return name.replace(" ", "") if ignore_spaces else name


def _folded_key(parts: list[str], ignore_spaces: bool) -> list[str]:
    """A trait and its specialties, folded, with the specialties sorted, for
    comparing keys regardless of specialty order."""
    folded = [_fold(part, ignore_spaces) for part in parts]
    return [folded[0], *sorted(folded[1:])]


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
        return self.type in (VCharTrait.Type.CUSTOM.value, VCharTrait.Type.SKILL.value)

    @property
    def has_specialties(self) -> bool:
        """Whether the trait has any specialties."""
        return bool(self.raw_subtraits)

    @property
    def specialties(self) -> list[str]:
        """The trait's specialties."""
        return self.raw_subtraits.copy()

    def add_powers(self, powers: str | list[str]):
        """Add powers to the Discipline."""
        if not self.is_discipline:
            raise errors.SpecialtiesNotAllowed("Only Disciplines may have powers.")

        self._add_subtraits(powers)

    def add_specialties(self, specialties: str | list[str]):
        """Add specialties to the trait."""
        if not self.specialties_allowed:
            raise errors.SpecialtiesNotAllowed(
                "Only skills and custom traits may have specialties."
            )
        self._add_subtraits(specialties)

    def _add_subtraits(self, specialties: str | list[str] | set[str]):
        """Add a specialty or a power."""
        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        # Compared as lookups compare them, so "BigCats" is Big Cats
        for specialty in specialties:
            if _fold(specialty, True) not in (_fold(s, True) for s in self.raw_subtraits):
                self.raw_subtraits.append(specialty)

        self.raw_subtraits.sort()

    def remove_specialties(self, specialties: str | list[str] | set[str]):
        """Remove specialties from the trait."""
        if isinstance(specialties, str):
            specialties = {specialties}
        else:
            specialties = set(specialties)

        # Compared as lookups compare them, so "BigCats" removes Big Cats
        for specialty in (_fold(s, True) for s in specialties):
            current = [_fold(spec, True) for spec in self.raw_subtraits]
            try:
                index = current.index(specialty)
                del self.raw_subtraits[index]
            except ValueError:
                continue

    def matching(self, identifier: str, exact: bool, *, ignore_spaces=False) -> list[TraitMatch]:
        """Returns the fully qualified name if a string matches, or None. With
        ignore_spaces, names match without their spaces: "animalken" matches
        Animal Ken."""
        matches = []
        if groups := self.expanding(identifier, exact, False, ignore_spaces=ignore_spaces):
            # Specialties may come in any order, so exactness compares them
            # folded and sorted on both sides. (Sorting before folding would
            # disagree: "Zebra" sorts before "apple", but "zebra" after.)
            normalized = _folded_key(identifier.split(VCharTrait.DELIMITER), ignore_spaces)

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
                    TraitMatch(
                        name=full_name,
                        rating=rating,
                        exact=normalized == _folded_key(expanded, ignore_spaces),
                        key=key,
                        type=self.type,
                        discipline=self.is_discipline,
                    )
                )
        return matches

    @overload
    def expanding(
        self,
        identifier: str,
        exact: bool,
        join: Literal[True] = ...,
        *,
        ignore_spaces: bool = ...,
    ) -> list[str]: ...
    @overload
    def expanding(
        self,
        identifier: str,
        exact: bool,
        join: Literal[False],
        *,
        ignore_spaces: bool = ...,
    ) -> list[list[str]]: ...

    def expanding(
        self,
        identifier: str,
        exact: bool,
        join: bool = True,
        *,
        ignore_spaces=False,
    ) -> list[str] | list[list[str]]:
        """Expand a dot-delimited identifier into all matching fully qualified
        trait.specialty names.

        Example: "melee.sw" -> ["Melee.Swords"], "occ.k" -> ["Occult.Kindred"]

        Args:
            identifier: Dot-delimited string, e.g. "melee.swords".
            exact: Require exact matches (case-insensitive) vs prefix matching.
            join: If True, return joined strings. If False, return split lists.
            ignore_spaces: Compare names without their spaces.

        Returns:
            Empty list on no match. Otherwise, all matching expansions.
        """
        tokens = [_fold(t, ignore_spaces) for t in identifier.split(VCharTrait.DELIMITER)]

        # The comparison function takes a token and an instance var
        if exact:

            def comp(t: str, i: str) -> bool:
                return t == _fold(i, ignore_spaces)
        else:

            def comp(t: str, i: str) -> bool:
                return _fold(i, ignore_spaces).startswith(t)

        if comp(tokens[0], self.name):
            # Each selection is a set of distinct specialties, one per token
            # so far. A token may match several, so equal selections merge as
            # we go: listing every combination first would grow with their
            # product ("b.k.k.k..." with Kindred and Kine doubles each time).
            selections: set[frozenset[str]] = {frozenset()}
            for token in tokens[1:]:
                found = [spec for spec in self.raw_subtraits if comp(token, spec)]
                selections = {
                    selection | {spec}
                    for selection in selections
                    for spec in found
                    if spec not in selection
                }
                if len(selections) > MAX_SUBTRAIT_MATCHES:
                    # Too vague to list; keep the first few, so it fails as
                    # ambiguous without the cost of every combination
                    selections = set(sorted(selections, key=sorted)[:MAX_SUBTRAIT_MATCHES])

            matches = sorted([self.name, *sorted(selection)] for selection in selections)

            if join:
                return [VCharTrait.DELIMITER.join(match) for match in matches]
            return matches

        # No matches
        return []
