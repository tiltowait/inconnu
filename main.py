"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import json
import os

import discord
from bson.objectid import ObjectId
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

import bot
import inconnu
from config import SHOW_TEST_ROUTES
from logger import Logger

app = FastAPI(openapi_url=None)
app.mount("/web", StaticFiles(directory="web"), name="web")

templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Debug page or (if live) redirect to the documentation."""
    if SHOW_TEST_ROUTES:
        with open("web/index.html", "r", encoding="utf-8") as html:
            return html.read()
    return RedirectResponse("https://docs.inconnu.app", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/profile/{charid}", response_class=HTMLResponse)
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


# Patch discord.Interaction
def respond(self, *args, **kwargs):
    """Returns either the InteractionResponse or followup's send method."""
    if self.response.is_done():
        return self.followup.send(*args, **kwargs)
    return self.response.send_message(*args, **kwargs)


discord.Interaction.respond = respond
Logger.info("MAIN: Patched discord.Interaction")


if __name__ == "__main__":
    # DEBUG MODE. Does not spin up the web server.
    bot.bot.run(os.environ["INCONNU_TOKEN"])
else:
    # PRODUCTION. Called with inconnu.sh (or uvicorn main:app).
    asyncio.create_task(bot.run())
