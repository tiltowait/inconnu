"""Character API routes."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import API_KEY
from models import VChar
from services import char_mgr
from web.routers.characters.models import (
    AuthorizedCharacter,
    AuthorizedCharacterList,
    CharacterGuild,
)

DISCORD_HEADER = "X-Discord-User-ID"

router = APIRouter()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
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
