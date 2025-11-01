"""The Inconnu API endpoints."""

import functools
import os
import re
from datetime import datetime
from json import dumps
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import aiohttp
import async_timeout
from dotenv import load_dotenv
from loguru import logger

if TYPE_CHECKING:
    from inconnu.models import VChar

load_dotenv()


def normalize_url(url: str) -> str:
    """Return a normalized URL with scheme and trailing slash."""
    url = url.strip("/")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    return url + "/"


# An argument can be made that these should simply live with their appropriate
# command counterparts, but I see a value in keeping them together.

HEADER = {"Content-Type": "application/json"}
BASE_API = normalize_url(os.getenv("FC_API", "http://127.0.0.1:8080/"))
BUCKET = "pcs.inconnu.app"  # The name of the bucket where the images live


class ApiError(Exception):
    """An exception raised when there's an error with the API."""


def measure(func):
    """A decorator that measures API response time."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = datetime.now()
        val = await func(*args, **kwargs)
        end = datetime.now()

        logger.info("API: {} finished in {}", kwargs["path"], end - start)

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
    new_url = await _post(path="/image/upload", data=dumps(payload))
    return new_url


async def delete_single_faceclaim(image: str) -> bool:
    """Delete a single faceclaim image."""
    url = urlparse(image)
    if url.netloc != BUCKET:
        return False

    if (match := re.match(r"/([A-F0-9a-f]+/[A-F0-9a-f]+\.webp)$", url.path)) is None:
        return False

    key = match.group(1)
    res = await _delete(path=f"/image/{key}")
    logger.debug("API: {}", res)

    return True


async def delete_character_faceclaims(character: "VChar"):
    """Delete all of a character's faceclaims."""
    res = await _delete(path=f"/character/{character.id}")
    del character.profile.images[:]
    await character.commit()
    logger.info("API: {}", res)


@measure
async def _post(*, path: str, data: dict) -> str:
    """Send an API POST request."""
    logger.debug("API: POST to {} with {}", path, str(data))
    url = BASE_API + path.lstrip("/")

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=HEADER) as session:
            async with session.post(url, data=data) as response:
                json = await response.json()

                if not response.ok:
                    raise ApiError(str(json))
                return json


@measure
async def _delete(*, path: str) -> str:
    """Send an API DELETE request."""
    logger.debug("API: DELETE to {}", path)
    url = BASE_API + path.lstrip("/")

    async with async_timeout.timeout(60):
        async with aiohttp.ClientSession(headers=HEADER) as session:
            async with session.delete(url) as response:
                json = await response.json()

                if not response.ok:
                    raise ApiError(str(json))
                return json
