"""FastAPI server."""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routers import base, characters, posts, profiles, roleposts

load_dotenv()

app = FastAPI(openapi_url=None)
app.mount("/public", StaticFiles(directory="./src/web/public"), name="public")
app.include_router(base.router)
app.include_router(characters.router)
app.include_router(posts.router)
app.include_router(profiles.router)
app.include_router(roleposts.router)
