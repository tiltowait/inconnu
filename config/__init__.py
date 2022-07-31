"""Basic bot config."""

import os

from dotenv import load_dotenv

from logger import Logger

load_dotenv()

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]
    Logger.info("MAIN: Debugging on %s", DEBUG_GUILDS)
else:
    DEBUG_GUILDS = None
