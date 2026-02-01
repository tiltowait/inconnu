"""Character API router."""

from typing import Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

import inconnu
from config import API_KEY
from models import VChar
from services import char_mgr

router = APIRouter()


class Guild(BaseModel):
    """Guild data for the character endpoints."""

    id: int
    name: str
    icon: Optional[str]


class CharacterReturn(BaseModel):
    """The character data for /characters/{oid}."""

    guild: Guild
    character: VChar


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """Validates the API bearer token."""
    if credentials.credentials != API_KEY:
        raise HTTPException(401, detail="Invalid authentication token")
    return credentials


@router.get("/characters/{oid}")
async def get_character(
    request: Request,
    oid: PydanticObjectId,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> CharacterReturn:
    """Returns a given character if it belongs to the authed user."""
    user_id = request.headers.get("X-Discord-User-ID")
    if user_id is None:
        raise HTTPException(400, detail="Missing user ID")

    char = await char_mgr.id_fetch(oid)
    if char is None:
        raise HTTPException(404, detail="Character not found")
    if int(user_id) != char.user:
        raise HTTPException(403, detail="User does not own character")

    guild = await inconnu.bot.get_or_fetch_guild(char.guild)
    if guild is not None:
        icon = guild.icon.url if guild.icon else None
        guild_data = Guild(id=guild.id, name=guild.name, icon=icon)
    else:
        guild_data = Guild(id=char.guild, name="Unknown", icon=None)

    return CharacterReturn(
        guild=guild_data,
        character=char,
    )
