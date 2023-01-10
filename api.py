"""The Inconnu API endpoints."""

import functools
import glob
import os
import re
from datetime import datetime
from json import dumps

import aiohttp
import async_timeout

from logger import Logger

# An argument can be made that these should simply live with their appropriate
# command counterparts, but I see a value in keeping them together.

AUTH_HEADER = {"Authorization": os.environ["INCONNU_API_TOKEN"]}
BASE_API = "https://api.inconnu.app/"


class ApiError(Exception):
    """An exception raised when there's an error with the API."""


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
    new_url = await _post(path="/faceclaim/upload", data=dumps(payload))

    return new_url


async def delete_single_faceclaim(image: str) -> bool:
    """Delete a single faceclaim image."""
    if not image.startswith("https://pcs.inconnu.app"):
        return False

    if (match := re.search(r"([A-F0-9a-f]+/[A-F0-9a-f]+\.webp)$", image)) is None:
        return False

    key = match.group(1)
    res = await _delete(path=f"/faceclaim/delete/{key}")
    Logger.debug("API: %s", res)

    return True


async def delete_character_faceclaims(character: "VChar"):
    """Delete all of a character's faceclaims."""
    res = await _delete(path=f"/faceclaim/delete/{character.id}/all")
    Logger.info("API: %s", res)


async def upload_logs():
    """Upload log files."""
    Logger.info("API: Uploading logs")
    try:
        logs = sorted(glob.glob("./logs/*.txt"))
        for log in logs:
            with open(log, "rb") as handle:
                payload = {"log_file": handle}
                res = await _post(path="/log/upload", data=payload)
                Logger.info("API: %s", res)

        if len(logs) > 1:
            # Remove all but the most recent log file
            for log in logs[:-1]:
                Logger.info("API: Deleting old log: %s", log)
                os.unlink(log)
        elif not logs:
            Logger.error("API: No log files found")
            return False

        # Logs all uploaded successfully
        return True

    except ApiError as err:
        Logger.error("API: %s", str(err))
        return False


@measure
async def _post(*, path: str, data: dict) -> str:
    """Send an API POST request."""
    Logger.debug("API: POST to %s with %s", path, str(data))
    url = BASE_API + path.lstrip("/")

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=AUTH_HEADER) as session:
            async with session.post(url, data=data) as response:
                json = await response.json()

                if not response.ok:
                    raise ApiError(str(json))
                return json


@measure
async def _delete(*, path: str) -> str:
    """Send an API DELETE request."""
    Logger.debug("API: DELETE to %s", path)
    url = BASE_API + path.lstrip("/")

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=AUTH_HEADER) as session:
            async with session.delete(url) as response:
                json = await response.json()

                if not response.ok:
                    raise ApiError(str(json))
                return json
