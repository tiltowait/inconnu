"""Character API router."""

from typing import Optional, Self

import discord
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

import inconnu
from config import API_KEY
from models import VChar
from services import char_mgr

DISCORD_HEADER = "X-Discord-User-ID"

router = APIRouter()


class Guild(BaseModel):
    """Guild data for the character endpoints."""

    id: int
    name: str
    icon: Optional[str]

    @classmethod
    async def fetch(cls, id: int) -> Self:
        """Fetch guild data from Discord."""
        try:
            # This method raises, despite the docs' indication otherwise, so we
            # have to wrap it in a try, irkshome though that is.
            guild = await inconnu.bot.get_or_fetch_guild(id)
            if guild is None:
                # This can probably never happen, but the return type hints
                # are wrong
                return cls.unknown(id)
            return cls.create(guild)
        except Exception:
            return cls.unknown(id)

    @classmethod
    def create(cls, guild: discord.Guild) -> Self:
        """Create from a real Discord guild object."""
        icon = guild.icon.url if guild.icon else None
        return cls(id=guild.id, name=guild.name, icon=icon)

    @classmethod
    def unknown(cls, id: int) -> Self:
        """Return generic data."""
        return cls(id=id, name="Unknown", icon=None)


class CharacterReturn(BaseModel):
    """The character data for /characters/{oid}."""

    guild: Guild
    character: VChar


class CharacterList(BaseModel):
    """The character data for /characters."""

    guilds: list[Guild]
    characters: list[VChar]


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
async def get_character_list(user_id: int = Depends(get_authenticated_user)) -> CharacterList:
    """Get all of the user's characters."""

    guilds: dict[int, Guild] = {}
    chars = []
    async for char in VChar.find(VChar.user == user_id):
        if char.guild not in guilds:
            guild = await Guild.fetch(char.guild)
            guilds[char.guild] = guild
        chars.append(char)

    return CharacterList(guilds=list(guilds.values()), characters=chars)


@router.get("/characters/{oid}")
async def get_character(
    oid: PydanticObjectId,
    user_id: int = Depends(get_authenticated_user),
) -> CharacterReturn:
    """Returns a given character if it belongs to the authed user."""
    char = await char_mgr.id_fetch(oid)

    if char is None:
        raise HTTPException(404, detail="Character not found")
    if user_id != char.user:
        raise HTTPException(403, detail="User does not own character")

    guild = await Guild.fetch(char.guild)

    return CharacterReturn(
        guild=guild,
        character=char,
    )
