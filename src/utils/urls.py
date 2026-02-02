"""URL generation for web features."""

from beanie import PydanticObjectId
from bson import ObjectId

import config


def profile_url(charid: str | ObjectId | PydanticObjectId) -> str:
    """Generate a profile URL for the character."""
    return config.PROFILE_SITE + f"profile/{charid}"


def post_url(post_id: str | PydanticObjectId) -> str:
    """Generate a post history URL."""
    return config.PROFILE_SITE + f"post/{post_id}"


def wizard_url(token: str) -> str:
    """Generate a character creation wizard URL."""
    return config.APP_SITE + f"/wizard/{token}"
