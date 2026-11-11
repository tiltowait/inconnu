"""Integration key management and read-only history."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.exceptions import HTTPException
from loguru import logger

import errors
from models.integration import CreatedKey, KeyList, KeyRequest, RevokedKey, RollPage
from routes.auth import get_authenticated_user, verify_api_key
from routes.deps import get_bot
from services import integration_keys, integration_rolls
from services.integration_limits import limits

if TYPE_CHECKING:
    from bot import InconnuBot

router = APIRouter(dependencies=[Depends(verify_api_key)])


@contextmanager
def http_errors() -> Iterator[None]:
    """Translate integration errors into HTTP responses."""
    try:
        yield
    except errors.IntegrationError as err:
        headers = {"Retry-After": str(err.retry_after)} if err.retry_after else None
        raise HTTPException(err.status, detail=err.detail, headers=headers) from err


@router.get("/integration-keys")
async def list_keys(
    response: Response,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    owner_id: int = Depends(get_authenticated_user),
) -> KeyList:
    """List only the authenticated account's keys and eligible channels."""
    response.headers["Cache-Control"] = "no-store"
    with http_errors():
        limits.check_management_rate_limit(owner_id)
        return KeyList(
            keys=await integration_keys.list_keys(owner_id),
            channels=await integration_keys.channel_choices(bot, owner_id),
        )


@router.post("/integration-keys", status_code=201)
async def create_key(
    data: KeyRequest,
    response: Response,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    owner_id: int = Depends(get_authenticated_user),
) -> CreatedKey:
    """Create a scoped credential for the authenticated account."""
    response.headers["Cache-Control"] = "no-store"
    with http_errors():
        limits.check_management_rate_limit(owner_id)
        limits.check_create_rate_limit(owner_id)
        return await integration_keys.create_key(bot, owner_id, data)


@router.post("/integration-keys/{key_id}/revoke")
async def revoke_key(
    key_id: str,
    response: Response,
    owner_id: int = Depends(get_authenticated_user),
) -> RevokedKey:
    """Revoke an owned credential independently of roll traffic admission."""
    response.headers["Cache-Control"] = "no-store"
    with http_errors():
        limits.check_management_rate_limit(owner_id)
        return RevokedKey(key=await integration_keys.revoke_key(owner_id, key_id))


@router.get("/integration-rolls")
async def rolls(
    response: Response,
    bot: Annotated[InconnuBot, Depends(get_bot)],
    start: datetime,
    end: datetime,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    secret: Annotated[str | None, Header(alias="X-Integration-Key")] = None,
) -> RollPage:
    """Authenticate and authorize one channel before reading bounded roll history."""
    response.headers["Cache-Control"] = "no-store"
    with http_errors():
        try:
            key = await integration_keys.authenticate(secret)
        except errors.IntegrationError as err:
            if err.status == 401:
                limits.failed_authentication()
            raise
        async with limits.admit_request(str(key["_id"]), key["owner_id"]):
            await integration_keys.authorize_channel(
                bot,
                key["owner_id"],
                key["guild_id"],
                key["channel_id"],
            )
            result = await integration_rolls.history(key, start, end, limit, cursor)
            logger.info(
                "Read integration rolls for key {}: {} results", key["_id"], len(result.rolls)
            )
            return result
