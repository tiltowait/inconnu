"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import json
import os
from typing import Dict, List

import markdown
from bson.objectid import ObjectId
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import bot
import inconnu

app = FastAPI(openapi_url=None)
app.mount("/web/favicon", StaticFiles(directory="web/favicon"), name="web/favicon")


if "DEBUG" in os.environ:
    # We don't want these development endpoints in the final API

    @app.get("/", response_class=HTMLResponse)
    async def home():
        """Basic webpage with example."""
        with open("web/index.html", "r", encoding="utf-8") as html:
            return html.read()

    @app.get("/test", response_class=HTMLResponse)
    async def offline_page():
        """Generate an offline test page."""
        with open("web/snippets.json", "r", encoding="utf-8") as file:
            profile = json.load(file)["sample"]
            profile["user"] = 0
            profile["guild"] = 0
            return prepare_html(profile)


@app.get("/profile/{charid}", response_class=HTMLResponse)
async def display_character_profile(charid: str):
    """Display character biography detail."""
    if not ObjectId.is_valid(charid):
        raise HTTPException(400, detail="Improper character ID.")

    oid = ObjectId(charid)
    bio = await inconnu.db.characters.find_one(
        {"_id": oid},
        {"name": 1, "user": 1, "guild": 1, "profile": 1},
    )
    if bio is None:
        raise HTTPException(404, detail="Character not found.")

    # Got the character; return the HTML
    return prepare_html(bio)


def prepare_html(bio: Dict[str, str | dict[str, str]]) -> str:
    """Prep the character HTML page."""
    with open("web/snippets.json", "r", encoding="utf-8") as snippets:
        snippets = json.load(snippets)

        # Basic profile info
        name = bio["name"]
        profile = bio.get("profile", {})
        biography = markdown.markdown(profile.get("biography", "")) or snippets["unset"]
        description = markdown.markdown(profile.get("description", "")) or snippets["unset"]

        # Get the profile image by template
        if image := profile.get("images", [""]):
            image_prop = snippets["image_prop"].format(source=image[0])
            image = snippets["profile_image"].format(source=image[0], name=name)
        else:
            image_prop = ""
            image = snippets["no_profile_image"]

        # Generate the ownership string and icons
        guild = bot.bot.get_guild(bio["guild"])
        user = guild.get_member(bio["user"]) if guild is not None else None
        icons = get_icons(snippets, user, guild)

        if guild is None:
            ownership = snippets["unknown"]
        elif user is None:
            ownership = snippets["unowned"].format(guild=guild.name)
        elif user == bot.bot.user:
            ownership = snippets["spc"].format(guild=guild.name)
        else:
            # Guild found, user found, user not the bot
            ownership = snippets["owned"].format(user=user.name, guild=guild.name)

    with open("web/profile.html", "r", encoding="utf-8") as html_file:
        html = html_file.read()
        return html.format(
            name=name,
            url=inconnu.profile_url(bio["_id"]),
            image_prop=image_prop,
            biography=biography,
            description=description,
            image=image,
            ownership=ownership,
            icons="\n".join(icons),
        )


def get_icons(snippets, user, guild) -> List[str]:
    """Get the icons for the user and guild."""
    icons = []
    if user is not None:
        icons.append(
            snippets["icon"].format(source=inconnu.get_avatar(user), name=user.display_name)
        )
    if guild is not None:
        icons.append(snippets["icon"].format(source=guild.icon, name=guild.name))

    return icons


if __name__ == "__main__":
    # DEBUG MODE. Does not spin up the web server.
    bot.setup()
    bot.bot.run(os.environ["INCONNU_TOKEN"])
else:
    # PRODUCTION. Called with inconnu.sh (or uvicorn main:app).
    asyncio.create_task(bot.run())
