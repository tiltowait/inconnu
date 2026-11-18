"""Web API authentication utilities."""

import hmac
from typing import TYPE_CHECKING, Annotated

import discord
from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from config import settings
from routes.deps import get_bot
from utils.permissions import has_supporter_role

if TYPE_CHECKING:
    from bot import InconnuBot

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


async def is_supporter(bot: InconnuBot, user_id: int) -> bool:
    """Whether the user has the supporter role on the support server. Users
    not on it never are."""
    guild = await bot.get_or_fetch_guild(settings.supporter_guild)
    if guild is None:
        logger.warning("Support server {} not found", settings.supporter_guild)
        return False

    member = await guild.get_or_fetch(discord.Member, user_id)
    return member is not None and has_supporter_role(member)


async def require_supporter(
    user_id: Annotated[int, Depends(get_authenticated_user)],
    bot: Annotated[InconnuBot, Depends(get_bot)],
):
    """Refuse requests from users who aren't supporters."""
    if not await is_supporter(bot, user_id):
        raise HTTPException(403, detail="This feature is for supporters only")
