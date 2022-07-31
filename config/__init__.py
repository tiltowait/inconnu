"""Basic bot config."""

import os
from typing import Optional

from dotenv import load_dotenv

from logger import Logger

load_dotenv()

DEBUG_GUILDS: Optional[list] = None

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]
    Logger.info("MAIN: Debugging on %s", DEBUG_GUILDS)
