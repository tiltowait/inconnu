"""Basic bot config."""

import os
from typing import Optional

from dotenv import load_dotenv

from logger import Logger

load_dotenv()

DEBUG_GUILDS: Optional[list] = None
ADMIN_GUILD = int(os.environ["ADMIN_SERVER"])

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]
    Logger.info("MAIN: Debugging on %s", DEBUG_GUILDS)


def aws_asset(path: str):
    """Returns the AWS URL for the given path."""
    base = "https://inconnu.s3-us-west-1.amazonaws.com/assets/"
    if path[0] == "/":
        path = path[1:]
    return base + path
