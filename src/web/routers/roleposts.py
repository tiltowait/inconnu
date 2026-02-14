"""Rolepost changelogs routing."""

from datetime import datetime
from typing import Optional

import discord
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import AnyUrl, BaseModel

import inconnu
from models import RPPost
from models.rppost import PostHistoryEntry
from services.wizard import CharacterGuild
from utils.discord_helpers import get_avatar
from web.auth import verify_api_key
from web.routers.characters.models import OwnerData

router = APIRouter()


class CharData(BaseModel):
    """Basic character info."""

    id: PydanticObjectId
    name: str


class Changelog(BaseModel):
    """Rolepost changelog response model."""

    guild: CharacterGuild
    poster: Optional[OwnerData]
    channel: str
    character: CharData
    url: Optional[AnyUrl]
    history: list[PostHistoryEntry]
    deletion_date: Optional[datetime]


@router.get("/changelog/{oid}")
async def get_rolepost(
    oid: PydanticObjectId, _: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Fetch Rolepost data."""
    rolepost = await RPPost.find_one(RPPost.id == oid)
    if rolepost is None:
        raise HTTPException(404, detail="Rolepost not found")

    guild = await inconnu.bot.get_or_fetch_guild(rolepost.guild)
    if guild is None:
        raise HTTPException(410, detail="Inconnu is not in this guild.")

    channel = await guild.get_or_fetch(discord.TextChannel, rolepost.channel)
    if channel is None:
        raise HTTPException(410, detail="This post's channel was deleted.")

    user = guild.get_member(rolepost.user)
    if user is not None:
        owner_data = OwnerData(
            id=str(user.id),
            name=user.display_name,
            icon=get_avatar(user).url,
        )
    else:
        owner_data = None

    char_data = CharData(id=rolepost.header.charid, name=rolepost.header.char_name)

    # The RPPost's history doesn't contain the current content
    current = PostHistoryEntry(
        date=rolepost.date_modified or rolepost.date,
        content=rolepost.content,
    )
    history = [current] + rolepost.history

    return Changelog(
        guild=CharacterGuild.create(guild),
        poster=owner_data,
        channel=channel.name,
        character=char_data,
        url=rolepost.url,
        history=history,
        deletion_date=rolepost.deletion_date,
    )
