"""URL generation for web features."""

from bson import ObjectId

import config


def profile_url(charid: str | ObjectId) -> str:
    """Generate a profile URL for the character."""
    return config.PROFILE_SITE + f"profile/{charid}"


def post_url(post_id: str) -> str:
    """Generate a post history URL."""
    return config.PROFILE_SITE + f"post/{post_id}"
