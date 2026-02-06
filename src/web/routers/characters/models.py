"""Pydantic models for character API endpoints."""

from typing import Optional, Self

import discord
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator, model_validator

import inconnu
from constants import ATTRIBUTES, SKILLS
from errors import CharacterError
from models import VChar
from models.vchardocs import VCharProfile, VCharSplat, VCharTrait
from services.wizard import CharacterGuild
from utils import get_avatar
from utils.validation import valid_name, validate_specialty_names, validate_trait_names


class OwnerData(BaseModel):
    """Basic character ownership data."""

    id: str
    name: str
    icon: str

    @classmethod
    def from_user(cls, user: discord.Member) -> Self:
        """Create OwnerData from Discord Member object."""
        return cls(id=str(user.id), name=user.display_name, icon=get_avatar(user).url)

    @classmethod
    async def create(cls, guild_id: int, user_id: int) -> Self | None:
        """Create a CharacterOwner object."""
        guild = await inconnu.bot.get_or_fetch_guild(guild_id)
        if guild is None:
            return None
        user = await guild.get_or_fetch(discord.Member, user_id)
        if user is None:
            return None

        return cls.from_user(user)


class BaseProfile(BaseModel):
    """A base character model containing name, profile, and guild data."""

    id: PydanticObjectId
    spc: bool
    guild: CharacterGuild
    user: str
    name: str
    splat: str
    profile: VCharProfile

    @classmethod
    async def create(
        cls,
        char: VChar,
        guild: CharacterGuild | None = None,
    ) -> Self:
        """Construct a base profile."""
        if guild is None:
            guild = await CharacterGuild.fetch(char.guild)

        if char.id is None:
            raise CharacterError(f"{char.name} hasn't been saved to the database yet.")

        return cls(
            id=char.id,
            spc=char.is_spc,
            guild=guild,
            user=str(char.user),
            name=char.name,
            splat=char.splat,
            profile=char.profile,
        )


class ProfileWithOwner(BaseModel):
    """Character profile with ownership metadata for guild listings."""

    character: BaseProfile
    owner_data: Optional[OwnerData]


class AuthorizedCharacter(BaseModel):
    """The character data for /characters/{oid}."""

    guild: CharacterGuild
    owner: Optional[OwnerData]
    character: Optional[VChar]
    profile: Optional[BaseProfile]


class AuthorizedCharacterList(BaseModel):
    """The character data for /characters."""

    guilds: list[CharacterGuild]
    characters: list[VChar]


class AuthorizedGuildList(BaseModel):
    """Data returned by /characters/guild."""

    characters: list[BaseProfile]


class WizardSchema(BaseModel):
    """Data sent by the wizard endpoint."""

    spc: bool
    guild: CharacterGuild
    splats: list[VCharSplat] = list(VCharSplat)
    traits: list[VCharTrait] = [
        VCharTrait(name=trait, rating=1, type=VCharTrait.Type.ATTRIBUTE) for trait in ATTRIBUTES
    ] + [VCharTrait(name=trait, rating=1, type=VCharTrait.Type.SKILL) for trait in SKILLS]


class CreationBody(BaseModel):
    """A character creation request."""

    name: str
    splat: VCharSplat
    health: int = Field(ge=4, le=20)
    willpower: int = Field(ge=2, le=10)
    humanity: int = Field(ge=0, le=10)
    blood_potency: int = Field(ge=0, le=10)
    convictions: list[str] = Field(max_length=3)
    biography: str = Field(max_length=1024)
    description: str = Field(max_length=24)
    traits: list[VCharTrait]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize character name."""
        normalized = " ".join(v.split())
        if not valid_name(normalized):
            raise ValueError(
                "Invalid name: must be 1-30 characters and contain only letters, "
                "numbers, spaces, hyphens, underscores, and apostrophes"
            )
        return normalized

    @field_validator("traits")
    @classmethod
    def validate_traits(cls, v: list[VCharTrait]) -> list[VCharTrait]:
        """Validate all trait names and specialties."""
        # Validate trait names
        trait_names = [trait.name for trait in v]
        validate_trait_names(*trait_names)

        # Validate specialties
        for trait in v:
            if trait.raw_subtraits:
                # Only skills, custom traits, and disciplines can have subtraits
                if trait.type not in [
                    VCharTrait.Type.SKILL,
                    VCharTrait.Type.CUSTOM,
                    VCharTrait.Type.DISCIPLINE,
                ]:
                    raise ValueError(
                        f"Trait `{trait.name}` of type `{trait.type}` cannot have subtraits."
                    )
                # Validate specialty names
                validate_specialty_names(*trait.raw_subtraits)

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
        if self.splat in [VCharSplat.MORTAL, VCharSplat.GHOUL]:
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
