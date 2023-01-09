"""The Inconnu API endpoints."""

import functools
import os
from datetime import datetime

import aiohttp
import async_timeout

import inconnu
from logger import Logger

# An argument can be made that these should simply live with their appropriate
# command counterparts, but I see a value in keeping them together.

AUTH_HEADER = {"Authorization": os.environ["INCONNU_API_TOKEN"]}
BASE_API = "https://api.inconnu.app/"


def measure(func):
    """A decorator that measures API response time."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = datetime.now()
        val = await func(*args, **kwargs)
        end = datetime.now()

        Logger.info("API: %s finished in %s", kwargs["path"], end - start)

        return val

    return wrapper


async def upload_faceclaim(character: "VChar", image_url: str) -> str:
    """Uploads a faceclaim to cloud storage."""
    payload = {
        "guild": character.guild,
        "user": character.user,
        "charid": character.id,
        "image_url": image_url,
    }
    new_url = await _post(path="/faceclaim/upload", payload=payload)

    return new_url


@measure
async def _post(*, path: str, payload: dict):
    """Send an API POST request."""
    Logger.debug("API: POST to %s with %s", path, payload)
    url = BASE_API + path.lstrip("/")

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=AUTH_HEADER) as session:
            async with session.post(url, json=payload) as response:
                json = await response.json()

                if not response.ok:
                    raise inconnu.errors.ApiError(str(json))
                return json
