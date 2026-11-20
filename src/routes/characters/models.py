"""Pydantic models for character API endpoints."""

from collections.abc import Iterator, Mapping
from typing import Literal, Self

from beanie import PydanticObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from constants import (
    ATTRIBUTES,
    MAX_CONVICTION_LENGTH,
    MAX_CONVICTIONS,
    MAX_HUMANITY,
    MAX_HUNGER,
    MAX_POTENCY,
    MAX_PROFILE_LENGTH,
    MAX_STAINS,
    MAX_THIN_BLOOD_POTENCY,
    MAX_TRAIT_RATING,
    SKILLS,
    core_trait,
    name_key,
)
from errors import CharacterError
from models import MAX_FRENZY_BONUS, FrenzyAdvantage, FrenzyPenalty, VChar
from models.vchar import Tracker
from models.vchardocs import VCharProfile, VCharSplat, VCharTrait
from routes.constraints import Constraints
from services import guild_cache
from services.guildcache import CachedMember
from services.wizard import CharacterGuild
from utils.validation import (
    MAX_NAME_LENGTH,
    valid_name,
    validate_specialty_names,
    validate_tracker,
    validate_trait_names,
)

# Traits the web app may set. Inherent traits (Hunger, Willpower, ...) are
# computed, never stored
EDITABLE_TRAIT_TYPES = {
    VCharTrait.Type.ATTRIBUTE,
    VCharTrait.Type.SKILL,
    VCharTrait.Type.DISCIPLINE,
    VCharTrait.Type.CUSTOM,
}
SUBTRAIT_TYPES = {VCharTrait.Type.SKILL, VCharTrait.Type.CUSTOM, VCharTrait.Type.DISCIPLINE}
# Keyed by name_key(), since lookups ignore case and spaces
CORE_TRAIT_TYPES = {name_key(name): VCharTrait.Type.ATTRIBUTE for name in ATTRIBUTES} | {
    name_key(name): VCharTrait.Type.SKILL for name in SKILLS
}
# Enough to wrap a full track twice over; a cap so huge counts can't build
# huge tracks
MAX_DAMAGE = 2 * max(VChar.MAX_HEALTH, VChar.MAX_WILLPOWER)

type ErrorLoc = tuple[int | str, ...]


def normalize_name(name: str) -> str:
    """Collapse a character name's whitespace, raising ValueError if the
    result isn't a valid name."""
    normalized = " ".join(name.split())
    if not valid_name(normalized):
        raise ValueError(
            f"Invalid name: must be 1-{MAX_NAME_LENGTH} characters and contain only letters, "
            "numbers, spaces, hyphens, underscores, and apostrophes"
        )
    return normalized


def trait_errors(
    traits: list[VCharTrait], kept: Mapping[str, list[str]] | None = None
) -> Iterator[tuple[ErrorLoc, str]]:
    """Yield every problem with a list of traits, each with its location in
    the list: (index, field) and a message. Checks names (format, reserved
    names, uniqueness), types, ratings (0-5), and specialties.

    Only skills, custom traits, and Disciplines may gain specialties. Other
    traits may keep the ones they have, given in kept by casefolded name."""
    kept = kept or {}
    seen: set[str] = set()
    for index, trait in enumerate(traits):
        # The validators raise SyntaxError for invalid characters
        try:
            validate_trait_names(trait.name)
            key = name_key(trait.name)
            if key in seen:
                raise ValueError(f"Duplicate trait: `{trait.name}`.")
            seen.add(key)
        except (SyntaxError, ValueError) as err:
            yield (index, "name"), str(err)

        if trait.type not in EDITABLE_TRAIT_TYPES:
            yield (index, "type"), f"`{trait.name}` can't be of type `{trait.type}`."
        elif (core_type := CORE_TRAIT_TYPES.get(name_key(trait.name))) is not None:
            if trait.type != core_type:
                yield (index, "type"), f"`{trait.name}` must be of type `{core_type}`."
        elif trait.type == VCharTrait.Type.ATTRIBUTE:
            yield (index, "type"), f"`{trait.name}` isn't an Attribute."

        if not 0 <= trait.rating <= MAX_TRAIT_RATING:
            yield (
                (index, "rating"),
                f"`{trait.name}` must be between 0 and {MAX_TRAIT_RATING}. (Got {trait.rating}.)",
            )

        if trait.raw_subtraits:
            if trait.type not in SUBTRAIT_TYPES:
                allowed = {s.casefold() for s in kept.get(trait.name.casefold(), [])}
                if any(s.casefold() not in allowed for s in trait.raw_subtraits):
                    yield (
                        (index, "subtraits"),
                        f"Trait `{trait.name}` of type `{trait.type}` cannot have subtraits.",
                    )
            try:
                validate_specialty_names(*trait.raw_subtraits)
            except (SyntaxError, ValueError) as err:
                yield (index, "subtraits"), str(err)


def long_convictions(
    convictions: list[str], kept: list[str] | None = None
) -> Iterator[tuple[int, int]]:
    """Yield the index and limit of each Conviction over its limit. Discord's
    modal didn't always enforce one, so, as the modal does now, a Conviction
    may be as long as the kept one in its slot. A kept Conviction is never
    too long, in any slot, since stored ones have no blanks to hold their
    places."""
    kept = kept or []
    unchanged = {" ".join(conviction.split()) for conviction in kept}
    for index, conviction in enumerate(convictions):
        if conviction in unchanged:
            continue
        limit = max(MAX_CONVICTION_LENGTH, len(kept[index]) if index < len(kept) else 0)
        if len(conviction) > limit:
            yield index, limit


def conviction_too_long(limit: int) -> str:
    """The error for a Conviction over its limit."""
    return f"Each conviction must be {limit} characters or less"


def with_core_traits(traits: list[VCharTrait]) -> list[VCharTrait]:
    """The traits, plus any missing core Attributes (at 1) and Skills (at 0),
    sorted by name. Core traits get their standard names, so an old spelling
    ("AnimalKen") replaces the core trait rather than joining it."""
    traits = [
        trait.model_copy(update={"name": standard})
        if (standard := core_trait(trait.name)) and standard != trait.name
        else trait
        for trait in traits
    ]
    present = {name_key(trait.name) for trait in traits}
    restored = [
        VCharTrait(name=name, rating=1, type=VCharTrait.Type.ATTRIBUTE)
        for name in ATTRIBUTES
        if name_key(name) not in present
    ] + [
        VCharTrait(name=name, rating=0, type=VCharTrait.Type.SKILL)
        for name in SKILLS
        if name_key(name) not in present
    ]
    return sorted(traits + restored, key=lambda t: t.name.casefold())


class OwnerData(BaseModel):
    """Basic character ownership data."""

    id: str
    name: str
    icon: str

    @classmethod
    def from_user(cls, user: CachedMember) -> Self:
        """Create OwnerData from Discord Member object."""
        return cls(id=str(user.id), name=user.name, icon=user.icon)

    @classmethod
    async def fetch(cls, guild_id: int, user_id: int) -> Self | None:
        """Create a CharacterOwner object."""
        user = await guild_cache.fetchmember(guild_id, user_id)
        if user is None:
            return None

        return cls.from_user(user)


class PublicCharacter(BaseModel):
    """Public character data without sensitive information, such as trait ratings."""

    id: PydanticObjectId
    user: str
    name: str
    splat: str
    profile: VCharProfile

    @classmethod
    def create(cls, char: VChar) -> Self:
        """Construct a base profile."""
        if char.id is None:
            raise CharacterError(f"{char.name} hasn't been saved to the database yet.")

        return cls(
            id=char.id,
            user=str(char.user),
            name=char.raw_name,
            splat=char.splat,
            profile=char.profile,
        )


class CharData(BaseModel):
    """Unified character response containing guild, owner, and character data."""

    guild: CharacterGuild
    owner: OwnerData | None
    character: VChar | PublicCharacter
    spc: bool

    @computed_field
    @property
    def type(self) -> Literal["full", "public"]:
        """The type of character model being returned."""
        return "full" if isinstance(self.character, VChar) else "public"


class GuildChars(BaseModel):
    """Data for all the characters belonging to a guild."""

    guild: CharacterGuild
    characters: list[CharData]


class UserCharData(BaseModel):
    """Intended to contain one user's characters as well as all the guilds the
    user shares with the bot.

    This model does contain redundant data: each character contains its own
    guild data and owner data, which leads to duplication. However, only 0.8%
    of users have more than 10 characters, and 87% have only 1 or 2. This
    small redundancy is acceptable given the reduced frontend logic complexity
    it enables."""

    guilds: list[CharacterGuild]
    characters: list[CharData]

    @model_validator(mode="after")
    def sort_guilds(self) -> Self:
        """Sort guilds alphabetically by name (case-insensitive)."""
        self.guilds = sorted(self.guilds, key=lambda g: g.name.casefold())
        return self


class WizardSchema(BaseModel):
    """Data sent by the wizard endpoint."""

    spc: bool
    guild: CharacterGuild
    splats: list[VCharSplat] = list(VCharSplat)
    constraints: Constraints = Field(default_factory=Constraints)
    traits: list[VCharTrait] = [
        VCharTrait(name=trait, rating=1, type=VCharTrait.Type.ATTRIBUTE) for trait in ATTRIBUTES
    ] + [VCharTrait(name=trait, rating=0, type=VCharTrait.Type.SKILL) for trait in SKILLS]


class CreationBody(BaseModel):
    """A character creation request."""

    name: str
    splat: VCharSplat
    health: int = Field(ge=VChar.MIN_HEALTH, le=VChar.MAX_HEALTH)
    willpower: int = Field(ge=VChar.MIN_WILLPOWER, le=VChar.MAX_WILLPOWER)
    humanity: int = Field(ge=0, le=MAX_HUMANITY)
    blood_potency: int = Field(ge=0, le=MAX_POTENCY)
    convictions: list[str] = Field(max_length=MAX_CONVICTIONS)
    biography: str = Field(max_length=MAX_PROFILE_LENGTH)
    description: str = Field(max_length=MAX_PROFILE_LENGTH)
    traits: list[VCharTrait]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize character name."""
        return normalize_name(v)

    @field_validator("traits")
    @classmethod
    def validate_traits(cls, v: list[VCharTrait]) -> list[VCharTrait]:
        """Validate all trait names and specialties."""
        # Pydantic only turns ValueErrors into validation errors (a 422 rather
        # than a 500), and one error per field
        for _, message in trait_errors(v):
            raise ValueError(message)
        return v

    @field_validator("convictions")
    @classmethod
    def validate_conviction_length(cls, v: list[str]) -> list[str]:
        """Validate each conviction's length."""
        if next(long_convictions(v), None) is not None:
            raise ValueError(conviction_too_long(MAX_CONVICTION_LENGTH))
        return v

    @model_validator(mode="after")
    def validate_blood_potency_for_splat(self):
        """Validate blood potency based on character splat."""
        if self.splat in (VCharSplat.MORTAL, VCharSplat.GHOUL):
            if self.blood_potency != 0:
                raise ValueError(f"{self.splat.value.title()}s must have blood potency of 0")
        elif self.splat == VCharSplat.THIN_BLOOD:
            if not (0 <= self.blood_potency <= MAX_THIN_BLOOD_POTENCY):
                raise ValueError(
                    f"Thin-bloods must have blood potency between 0 and {MAX_THIN_BLOOD_POTENCY}"
                )
        # VAMPIRE uses the default 0-10 range from Field constraint
        return self


class CreationSuccess(BaseModel):
    """Data returned to the web app indicating character creation success."""

    guild: CharacterGuild
    character_id: str
    character_name: str
    has_premium: bool


class EditProfile(BaseModel):
    """The editable parts of a character's profile. Images are edited
    elsewhere."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(max_length=MAX_PROFILE_LENGTH)
    biography: str = Field(max_length=MAX_PROFILE_LENGTH)


class EditBody(BaseModel):
    """A web app edit: every editable field, all at once. Checks that need the
    character (splat, names, Attribute specialties, Conviction lengths) happen
    in the route."""

    model_config = ConfigDict(extra="forbid")

    name: str
    health: str
    willpower: str
    humanity: int = Field(ge=0, le=MAX_HUMANITY)
    stains: int = Field(ge=0, le=MAX_STAINS)
    potency: int | None = Field(default=None, ge=0, le=MAX_POTENCY)
    hunger: int | None = Field(default=None, ge=0, le=MAX_HUNGER)
    convictions: list[str] = Field(max_length=MAX_CONVICTIONS)
    profile: EditProfile
    traits: list[VCharTrait]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize the name."""
        return normalize_name(v)

    @field_validator("health", "willpower")
    @classmethod
    def validate_track(cls, v: str, info: ValidationInfo) -> str:
        """Validate a tracker's boxes and length, returning it sorted."""
        track = validate_tracker(v)
        low, high = VChar.tracker_limits(Tracker(info.field_name))
        if not low <= len(track) <= high:
            raise ValueError(f"Must have between {low} and {high} boxes.")
        return track

    @field_validator("convictions")
    @classmethod
    def validate_convictions(cls, v: list[str]) -> list[str]:
        """Normalize the Convictions. Blanks are kept, so error locations match
        the app's slots; the route drops them, and checks their length."""
        return [" ".join(conviction.split()) for conviction in v]


class RouseBody(BaseModel):
    """A request for Rouse checks."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1, le=3)
    reroll: bool  # Re-roll failures, as high Blood Potency allows
    oblivion_stains: bool  # Apply the guild's Oblivion Stains, as for an Oblivion power


class RouseResult(BaseModel):
    """The outcome of Rouse checks. Ghouls take Aggravated Health damage
    instead, so they have no successes or failures."""

    successes: int
    failures: int
    hunger: int  # After the checks
    frenzy: bool  # At Hunger 5: a frenzy check, or torpor on a failure if awakening
    aggravated: int  # Ghouls' Aggravated Health damage
    stains: int  # Oblivion Stains gained
    degeneration: int  # Aggravated Willpower damage from those Stains
    dice: list[tuple[int, ...]]  # Each check's faces: the first, then any re-roll
    oblivion_faces: list[int]  # The server's Oblivion Stain faces, applied or not


class MendBody(BaseModel):
    """A request to heal damage. Health heals as /mend (Superficial) or
    /aggheal (Aggravated) do. Willpower recovers what /awaken would
    (Superficial) or one Aggravated, without Rouse Checks."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["superficial", "aggravated"]
    track: Tracker


class MendResult(BaseModel):
    """The outcome of healing damage."""

    track: str  # The healed track
    dice: list[int]  # Health's Rouse dice: one to mend, three for Aggravated; else none
    hunger: int  # After the Rouse Checks
    frenzy: bool  # A failed mending Rouse at Hunger 5 calls for a frenzy check (DC 4)
    torpor: bool  # Healing Aggravated damage pushed Hunger past 5


class DamageBody(BaseModel):
    """Damage to deal to a track. Superficial damage past the track's end
    wraps into Aggravated, as in /character update."""

    model_config = ConfigDict(extra="forbid")

    track: Tracker
    superficial: int = Field(ge=0, le=MAX_DAMAGE)
    aggravated: int = Field(ge=0, le=MAX_DAMAGE)

    @model_validator(mode="after")
    def validate_some_damage(self) -> Self:
        """There must be some damage to deal."""
        if self.superficial == 0 and self.aggravated == 0:
            raise ValueError("Deal at least one damage.")
        return self


class AmountBody(BaseModel):
    """An amount of Stains to add or Hunger to slake."""

    model_config = ConfigDict(extra="forbid")

    amount: int = Field(ge=1, le=10)


class SlakeResult(BaseModel):
    """The outcome of slaking Hunger."""

    frenzy: bool  # Slaking from Hunger 4+ calls for a frenzy check (DC 3)


class RemorseBody(BaseModel):
    """A request for a Remorse test, with /remorse's options."""

    model_config = ConfigDict(extra="forbid")

    min_override: int = Field(ge=1, le=5)  # The fewest dice to roll; normally 1
    lasombra_alt: bool  # The Lasombra alternative bane: Bane Severity fewer dice


class RemorseResult(BaseModel):
    """The outcome of a Remorse test. Either way, Stains are cleared."""

    remorseful: bool  # Passed, keeping Humanity
    dice: list[int]
    humanity: int  # After the test


class FrenzyBody(BaseModel):
    """A request for a frenzy check, with /frenzy's options. Unlike /frenzy,
    bonus dice and advantages may be combined."""

    model_config = ConfigDict(extra="forbid")

    difficulty: int = Field(ge=1, le=10)
    penalty: FrenzyPenalty | None = None  # Brujah: Bane Severity fewer dice; Malkavian: 2
    bonus: int = Field(default=0, ge=0, le=MAX_FRENZY_BONUS)  # Flat bonus dice
    advantages: set[FrenzyAdvantage] = set()  # Advantages' bonus dice, or The Dream's re-roll


class FrenzyResult(BaseModel):
    """The outcome of a frenzy check."""

    passed: bool  # Resisted frenzy
    critical: bool  # Resisted without losing a turn
    pool: int  # After the penalty and bonuses
    dice: list[int]  # The final faces
    original: list[int] | None  # The faces before The Dream's re-roll, if used
