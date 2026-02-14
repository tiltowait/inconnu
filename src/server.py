"""FastAPI server."""

from dotenv import load_dotenv
from fastapi import FastAPI

from routes import characters, roleposts

load_dotenv()

app = FastAPI(openapi_url=None)
app.include_router(characters.router)
app.include_router(roleposts.router)
