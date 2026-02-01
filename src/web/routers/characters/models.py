"""Pydantic models for character API endpoints."""

from pydantic import BaseModel, Field, field_validator

from constants import ATTRIBUTES, SKILLS
from models import VChar
from models.vchardocs import VCharSplat, VCharTrait
from services.wizard import CharacterGuild


class AuthorizedCharacter(BaseModel):
    """The character data for /characters/{oid}."""

    guild: CharacterGuild
    character: VChar


class AuthorizedCharacterList(BaseModel):
    """The character data for /characters."""

    guilds: list[CharacterGuild]
    characters: list[VChar]


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
    history: str = Field(max_length=24)
    traits: list[VCharTrait]

    @field_validator("convictions")
    @classmethod
    def validate_conviction_length(cls, v: list[str]) -> list[str]:
        """Validate each conviction is max 200 characters."""
        for conviction in v:
            if len(conviction) > 200:
                raise ValueError("Each conviction must be 200 characters or less")
        return v
