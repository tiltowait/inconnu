from bson.objectid import ObjectId
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

import bot
import inconnu
from web import templates

router = APIRouter()


@router.get("/profile/{charid}", response_class=HTMLResponse)
async def display_character_profile(request: Request, charid: str):
    """Display character biography detail."""
    if not ObjectId.is_valid(charid):
        raise HTTPException(400, detail="Improper character ID.")

    bio = await inconnu.db.characters.find_one(
        {"_id": ObjectId(charid)},
        {"name": 1, "user": 1, "guild": 1, "profile": 1},
    )
    if bio is None:
        raise HTTPException(404, detail="Character not found.")

    # Got the character; return the HTML
    return prepare_profile_page(request, bio)


def prepare_profile_page(request: Request, bio: dict[str, str | dict[str, str]]) -> str:
    """Prep the character HTML page."""
    name = bio["name"]
    profile = bio.get("profile", {})

    # Ownership data
    guild = bot.bot.get_guild(bio["guild"])
    user = guild.get_member(bio["user"]) if guild is not None else None

    return templates.TemplateResponse(
        "profile.html.jinja",
        {
            "request": request,
            "name": name,
            "profile": profile,
            "owner": user,
            "guild": guild,
            "spc": user == bot.bot.user,
            "url": inconnu.profile_url(bio["_id"]),
        },
    )
