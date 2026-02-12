"""Basic bot config."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("INCONNU_TOKEN", "")
API_KEY = os.environ.get("INCONNU_API_TOKEN", "")
DEBUG_GUILDS: Optional[list] = None
ADMIN_GUILD = int(os.environ["ADMIN_SERVER"])
SUPPORTER_GUILD = int(os.environ["SUPPORTER_GUILD"])
SUPPORTER_ROLE = int(os.environ["SUPPORTER_ROLE"])
PROFILE_SITE = os.environ.get("PROFILE_SITE", "http://localhost:8000/")
SHOW_TEST_ROUTES = "SHOW_TEST_ROUTES" in os.environ
APP_SITE = os.environ.get("APP_SITE", "http://localhost:5173")
GUILD_CACHE_LOC = os.environ.get("GUILD_CACHE_LOC", "file::memory:?cache=shared")

if PROFILE_SITE[-1] != "/":
    PROFILE_SITE += "/"

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]

PROD = not DEBUG_GUILDS


def web_asset(path: str):
    """Returns the AWS URL for the given path."""
    base = "https://assets.inconnu.app/"
    if path[0] == "/":
        path = path[1:]
    return base + path
