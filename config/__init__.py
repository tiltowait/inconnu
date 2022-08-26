"""Basic bot config."""

import os
from typing import Optional

from dotenv import load_dotenv

from logger import Logger

load_dotenv()

DEBUG_GUILDS: Optional[list] = None
ADMIN_GUILD = int(os.environ["ADMIN_SERVER"])
SUPPORTER_GUILD = int(os.environ["SUPPORTER_GUILD"])
SUPPORTER_ROLE = int(os.environ["SUPPORTER_ROLE"])
PROFILE_SITE = os.environ.get("PROFILE_SITE", "http://localhost:8000/")
SHOW_TEST_ROUTES = "SHOW_TEST_ROUTES" in os.environ

if SHOW_TEST_ROUTES:
    Logger.info("CONFIG: Showing test routes")

if PROFILE_SITE[-1] != "/":
    PROFILE_SITE += "/"

Logger.info("CONFIG: Profile site set to %s", PROFILE_SITE)

Logger.info("CONFIG: Admin guild: %s", ADMIN_GUILD)

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]
    Logger.info("CONFIG: Debugging on %s", DEBUG_GUILDS)


def aws_asset(path: str):
    """Returns the AWS URL for the given path."""
    base = "https://inconnu.s3-us-west-1.amazonaws.com/assets/"
    if path[0] == "/":
        path = path[1:]
    return base + path
