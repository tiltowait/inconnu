"""Pydantic models for character API endpoints."""

from pydantic import BaseModel

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
