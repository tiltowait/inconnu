"""Character profile router."""

from typing import TypedDict

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

import bot
import db
from utils.urls import profile_url
from web import object_id, templates

router = APIRouter()


class Bio(TypedDict):
    _id: ObjectId
    name: str
    guild: int
    user: int
    profile: dict[str, str | list[str]]


@router.get("/profile/{oid}", response_class=HTMLResponse)
async def display_character_profile(request: Request, oid: ObjectId = Depends(object_id)):
    """Display character biography detail."""
    bio = await db.characters.find_one(
        {"_id": ObjectId(oid)},
        {"name": 1, "user": 1, "guild": 1, "profile": 1},
    )
    if bio is None:
        raise HTTPException(404, detail="Character not found.")

    # Got the character; return the HTML
    return prepare_profile_page(request, bio)


def prepare_profile_page(request: Request, bio: Bio) -> str:
    """Prep the character HTML page."""
    name = bio["name"]
    profile = bio.get("profile", {})

    # Ownership data
    guild = bot.bot.get_guild(int(bio["guild"]))
    user = guild.get_member(bio["user"]) if guild is not None else None

    return templates.TemplateResponse(
        request,
        "profile.html.jinja",
        {
            "name": name,
            "profile": profile,
            "owner": user,
            "guild": guild,
            "spc": user == bot.bot.user,
            "url": profile_url(bio["_id"]),
        },
    )
