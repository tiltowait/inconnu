"""Character API routes."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import API_KEY
from constants import Damage
from models import VChar
from services import char_mgr, wizard_cache
from services.wizard import CharacterGuild
from web.routers.characters.models import (
    AuthorizedCharacter,
    AuthorizedCharacterList,
    CreationBody,
    CreationSuccess,
    WizardSchema,
)

DISCORD_HEADER = "X-Discord-User-ID"

router = APIRouter()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> HTTPAuthorizationCredentials:
    """Validates the API bearer token."""
    if credentials.credentials != API_KEY:
        raise HTTPException(401, detail="Invalid authentication token")
    return credentials


async def get_authenticated_user(
    request: Request,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> int:
    """Get the authenticated user ID from headers after verifying API key."""
    user_id = request.headers.get(DISCORD_HEADER)
    if user_id is None:
        raise HTTPException(400, detail="Missing user ID")
    return int(user_id)


# Getters


@router.get("/characters")
async def get_character_list(
    user_id: int = Depends(get_authenticated_user),
) -> AuthorizedCharacterList:
    """Get all of the user's characters."""

    guilds: dict[int, CharacterGuild] = {}
    chars = []
    async for char in VChar.find(VChar.user == user_id):
        if char.guild not in guilds:
            guild = await CharacterGuild.fetch(char.guild)
            guilds[char.guild] = guild
        chars.append(char)

    return AuthorizedCharacterList(guilds=list(guilds.values()), characters=chars)


@router.get("/characters/{oid}")
async def get_character(
    oid: PydanticObjectId,
    user_id: int = Depends(get_authenticated_user),
) -> AuthorizedCharacter:
    """Returns a given character if it belongs to the authed user."""
    char = await char_mgr.id_fetch(oid)

    if char is None:
        raise HTTPException(404, detail="Character not found")
    if int(user_id) != char.user:
        raise HTTPException(403, detail="User does not own character")

    guild = await CharacterGuild.fetch(char.guild)

    return AuthorizedCharacter(
        guild=guild,
        character=char,
    )


# Wizard


@router.get("/characters/wizard/{token}")
async def get_wizard(
    token: str,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> WizardSchema:
    """Get the character wizard schema."""
    wizard = wizard_cache.get(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")

    return WizardSchema(
        spc=wizard.spc,
        guild=wizard.guild,
    )


@router.post("/characters/wizard/{token}", status_code=201)
async def create_character(
    token: str,
    data: CreationBody,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> CreationSuccess:
    """Create the character and insert it into the database."""
    wizard = wizard_cache.pop(token)
    if wizard is None:
        raise HTTPException(404, detail="Unknown token. It may have expired.")

    character = VChar(
        guild=wizard.guild.id,
        user=wizard.user,
        raw_name=data.name,
        splat=data.splat,
        raw_humanity=data.humanity,
        health=data.health * Damage.NONE,
        willpower=data.willpower * Damage.NONE,
        potency=data.blood_potency,
    )
    await char_mgr.register(character)

    return CreationSuccess(
        guild=wizard.guild,
        character_id=str(character.id),
        character_name=character.name,
    )
