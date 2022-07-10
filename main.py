"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import json
import os
from typing import Dict

from bson.objectid import ObjectId
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import bot
import inconnu

app = FastAPI(openapi_url=None)
app.mount("/web/favicon", StaticFiles(directory="web/favicon"), name="web/favicon")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Basic webpage with example."""
    with open("web/index.html", "r", encoding="utf-8") as html:
        return html.read()


@app.get("/test", response_class=HTMLResponse)
async def offline_page():
    """Generate an offline test page."""
    with open("web/sample.json", "r", encoding="utf-8") as file:
        bio = json.load(file)
        return prepare_html(bio)


@app.get("/profile/{charid}", response_class=HTMLResponse)
async def display_character_bio(charid: str):
    """Display character biography detail."""
    if not ObjectId.is_valid(charid):
        raise HTTPException(400, detail="Improper character ID.")

    oid = ObjectId(charid)
    bio = await inconnu.db.characters.find_one(
        {"_id": oid},
        {"name": 1, "user": 1, "guild": 1, "biography": 1, "description": 1, "image": 1},
    )
    if bio is None:
        raise HTTPException(404, detail="Character not found.")

    # Got the character; return the HTML
    return prepare_html(bio)


def prepare_html(json: Dict[str, str]) -> str:
    """Prep the character HTML page."""
    name = json["name"]
    biography = json.get("biography") or gen_not_set()
    description = json.get("description") or gen_not_set()
    image = gen_img(json.get("image"), name)

    guild = bot.bot.get_guild(json["guild"])
    user = guild.get_member(json["user"])

    round = "img-fluid rounded-circle"

    with open("web/profile.html", "r", encoding="utf-8") as html_file:
        html = html_file.read()
        return html.format(
            name=name,
            biography=biography,
            description=description,
            image=image,
            guild_icon=gen_img(str(guild.icon), guild.name, img_class=round, size=32),
            guild_name=guild.name,
            user_avatar=gen_img(
                inconnu.get_avatar(user),
                user.display_name,
                img_class=round,
                size=32,
            ),
            user_name=user.display_name,
        )


def gen_not_set() -> str:
    """Generate a styled "Not set" text."""
    return '<em class="text-muted">Not set.</em>'


def gen_img(image: str, name: str, *, img_class="rounded img-fluid", size: int = None) -> str:
    """Generate the img tag or specify unset."""
    if image:
        if size is not None:
            size = f'width="{size}"'
        else:
            size = ""
        return f'<img src="{image}" alt="{name}" {size} class="{img_class}">'
    return '<p class="text-muted text-center"><em>No image set.</em></p>'


if __name__ == "__main__":
    # DEBUG MODE. Does not spin up the web server.
    bot.setup()
    bot.bot.run(os.environ["INCONNU_TOKEN"])
else:
    # PRODUCTION. Called with inconnu.sh (or uvicorn main:app).
    asyncio.create_task(bot.run())
