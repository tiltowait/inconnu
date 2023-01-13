"""Basic bot config."""

import json
import os
from typing import Optional

from dotenv import load_dotenv

from config import logging

load_dotenv()

DEBUG_GUILDS: Optional[list] = None
ADMIN_GUILD = int(os.environ["ADMIN_SERVER"])
SUPPORTER_GUILD = int(os.environ["SUPPORTER_GUILD"])
SUPPORTER_ROLE = int(os.environ["SUPPORTER_ROLE"])
PROFILE_SITE = os.environ.get("PROFILE_SITE", "http://localhost:8000/")
SHOW_TEST_ROUTES = "SHOW_TEST_ROUTES" in os.environ
GCP_SVC_ACCT: Optional[dict] = None

if PROFILE_SITE[-1] != "/":
    PROFILE_SITE += "/"

if (_debug_guilds := os.getenv("DEBUG")) is not None:
    DEBUG_GUILDS = [int(g) for g in _debug_guilds.split(",")]

if (_gcp := os.getenv("GCP_SVC_ACCT")) is not None:
    GCP_SVC_ACCT = json.loads(_gcp)


def web_asset(path: str):
    """Returns the AWS URL for the given path."""
    base = "https://assets.inconnu.app/"
    if path[0] == "/":
        path = path[1:]
    return base + path
