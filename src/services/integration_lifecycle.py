"""Revoke roll-export keys when guild access ends."""

from datetime import UTC, datetime

from loguru import logger

import db


async def revoke_for_guild(guild_id: int, owner_id: int | None = None) -> None:
    """Permanently revoke unrevoked keys for a guild or one departing member."""
    query = {"guild_id": guild_id, "revoked_at": None}
    if owner_id is not None:
        query["owner_id"] = owner_id
    now = datetime.now(UTC)
    result = await db.integration_keys.update_many(
        query,
        {
            "$set": {
                "active": False,
                "revoked_at": now.replace(microsecond=now.microsecond // 1000 * 1000),
            }
        },
    )
    if result.modified_count:
        logger.info(
            "Revoked {} integration keys for guild {} and departing user {}",
            result.modified_count,
            guild_id,
            owner_id,
        )
