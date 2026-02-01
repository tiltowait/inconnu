"""Pydantic models for character API endpoints."""

from pydantic import BaseModel

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
    traits: list[VCharTrait]
