"""URL generation for web features."""

from urllib.parse import urljoin

from beanie import PydanticObjectId
from bson import ObjectId

from config import settings


def profile_url(charid: str | ObjectId | PydanticObjectId) -> str:
    """Generate a profile URL for the character."""
    return urljoin(settings.profile_site, f"profile/{charid}")


def post_url(post_id: str | PydanticObjectId) -> str:
    """Generate a post history URL."""
    return urljoin(settings.profile_site, f"post/{post_id}")


def wizard_url(token: str) -> str:
    """Generate a character creation wizard URL."""
    return urljoin(settings.app_site, f"/wizard/{token}")


def web_asset(path: str) -> str:
    """Return the CDN URL for a static asset."""
    return urljoin("https://assets.inconnu.app/", path)
