"""Web API authentication utilities."""

import hmac
from typing import Annotated

from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from services.premium import is_supporter

DISCORD_HEADER = "X-Discord-User-ID"


async def verify_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> HTTPAuthorizationCredentials:
    """Validates the API bearer token."""
    if not hmac.compare_digest(credentials.credentials, settings.inconnu_api_token):
        raise HTTPException(401, detail="Invalid authentication token")
    return credentials


async def get_authenticated_user(
    request: Request,
    _: Annotated[HTTPAuthorizationCredentials, Depends(verify_api_key)],
) -> int:
    """Get the authenticated user ID from headers after verifying API key."""
    user_id = request.headers.get(DISCORD_HEADER)
    if user_id is None:
        raise HTTPException(400, detail="Missing user ID")
    return int(user_id)


async def require_supporter(user_id: Annotated[int, Depends(get_authenticated_user)]):
    """Refuse requests from users who aren't supporters."""
    if not is_supporter(user_id):
        raise HTTPException(403, detail="This feature is for supporters only")
