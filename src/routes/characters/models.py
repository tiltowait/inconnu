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

from constants import ATTRIBUTES, SKILLS
from errors import CharacterError
from models import VChar
from models.vchar import Tracker
from models.vchardocs import VCharProfile, VCharSplat, VCharTrait
from services import guild_cache
from services.guildcache import CachedMember
from services.wizard import CharacterGuild
from utils.validation import (
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
CORE_TRAIT_TYPES = {name.casefold(): VCharTrait.Type.ATTRIBUTE for name in ATTRIBUTES} | {
    name.casefold(): VCharTrait.Type.SKILL for name in SKILLS
}
MAX_CONVICTION_LENGTH = 200
MAX_PROFILE_LENGTH = 1024

type ErrorLoc = tuple[int | str, ...]


def normalize_name(name: str) -> str:
    """Collapse a character name's whitespace, raising ValueError if the
    result isn't a valid name."""
    normalized = " ".join(name.split())
    if not valid_name(normalized):
        raise ValueError(
            "Invalid name: must be 1-30 characters and contain only letters, "
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
            folded = trait.name.casefold()
            if folded in seen:
                raise ValueError(f"Duplicate trait: `{trait.name}`.")
            seen.add(folded)
        except (SyntaxError, ValueError) as err:
            yield (index, "name"), str(err)

        if trait.type not in EDITABLE_TRAIT_TYPES:
            yield (index, "type"), f"`{trait.name}` can't be of type `{trait.type}`."
        elif (core_type := CORE_TRAIT_TYPES.get(trait.name.casefold())) is not None:
            if trait.type != core_type:
                yield (index, "type"), f"`{trait.name}` must be of type `{core_type}`."
        elif trait.type == VCharTrait.Type.ATTRIBUTE:
            yield (index, "type"), f"`{trait.name}` isn't an Attribute."

        if not 0 <= trait.rating <= 5:
            yield (
                (index, "rating"),
                f"`{trait.name}` must be between 0 and 5. (Got {trait.rating}.)",
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


def with_core_traits(traits: list[VCharTrait]) -> list[VCharTrait]:
    """The traits, plus any missing core Attributes (at 1) and Skills (at 0),
    sorted by name."""
    present = {trait.name.casefold() for trait in traits}
    restored = [
        VCharTrait(name=name, rating=1, type=VCharTrait.Type.ATTRIBUTE)
        for name in ATTRIBUTES
        if name.casefold() not in present
    ] + [
        VCharTrait(name=name, rating=0, type=VCharTrait.Type.SKILL)
        for name in SKILLS
        if name.casefold() not in present
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
    traits: list[VCharTrait] = [
        VCharTrait(name=trait, rating=1, type=VCharTrait.Type.ATTRIBUTE) for trait in ATTRIBUTES
    ] + [VCharTrait(name=trait, rating=0, type=VCharTrait.Type.SKILL) for trait in SKILLS]


class CreationBody(BaseModel):
    """A character creation request."""

    name: str
    splat: VCharSplat
    health: int = Field(ge=VChar.MIN_HEALTH, le=VChar.MAX_HEALTH)
    willpower: int = Field(ge=VChar.MIN_WILLPOWER, le=VChar.MAX_WILLPOWER)
    humanity: int = Field(ge=0, le=10)
    blood_potency: int = Field(ge=0, le=10)
    convictions: list[str] = Field(max_length=3)
    biography: str = Field(max_length=1024)
    description: str = Field(max_length=1024)
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
        """Validate each conviction is max 200 characters."""
        for conviction in v:
            if len(conviction) > 200:
                raise ValueError("Each conviction must be 200 characters or less")
        return v

    @model_validator(mode="after")
    def validate_blood_potency_for_splat(self):
        """Validate blood potency based on character splat."""
        if self.splat in (VCharSplat.MORTAL, VCharSplat.GHOUL):
            if self.blood_potency != 0:
                raise ValueError(f"{self.splat.value.title()}s must have blood potency of 0")
        elif self.splat == VCharSplat.THIN_BLOOD:
            if not (0 <= self.blood_potency <= 2):
                raise ValueError("Thin-bloods must have blood potency between 0 and 2")
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
    character (splat, names, Attribute specialties) happen in the route."""

    model_config = ConfigDict(extra="forbid")

    name: str
    health: str
    willpower: str
    humanity: int = Field(ge=0, le=10)
    stains: int = Field(ge=0, le=10)
    potency: int | None = Field(default=None, ge=0, le=10)
    hunger: int | None = Field(default=None, ge=0, le=5)
    convictions: list[str] = Field(max_length=3)
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
        """Normalize the Convictions and drop blank ones, as the bot does."""
        convictions = [" ".join(conviction.split()) for conviction in v]
        for conviction in convictions:
            if len(conviction) > MAX_CONVICTION_LENGTH:
                raise ValueError(
                    f"Each conviction must be {MAX_CONVICTION_LENGTH} characters or less"
                )
        return [conviction for conviction in convictions if conviction]
