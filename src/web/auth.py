"""Web API authentication utilities."""

from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import API_KEY

DISCORD_HEADER = "X-Discord-User-ID"


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> HTTPAuthorizationCredentials:
    """Validates the API bearer token."""
    if credentials.credentials != API_KEY:
        raise HTTPException(401, detail="Invalid authentication token")
    return credentials


async def get_authenticated_user(
    request: Request,
    _: HTTPAuthorizationCredentials = Depends(verify_api_key),
) -> int:
    """Get the authenticated user ID from headers after verifying API key."""
    user_id = request.headers.get(DISCORD_HEADER)
    if user_id is None:
        raise HTTPException(400, detail="Missing user ID")
    return int(user_id)
