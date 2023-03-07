"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import asyncio
import os

import discord
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import bot
from logger import Logger
from web.routers import base, posts, profiles

app = FastAPI(openapi_url=None)
app.mount("/public", StaticFiles(directory="./web/public"), name="public")
app.include_router(base.router)
app.include_router(posts.router)
app.include_router(profiles.router)


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
elif "PYTEST" not in os.environ:
    # PRODUCTION. Called with inconnu.sh (or uvicorn main:app).
    asyncio.create_task(bot.run())
