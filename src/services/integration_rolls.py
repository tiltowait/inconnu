"""Bounded, current-state roll history."""

import base64
import binascii
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

import db
from errors import IntegrationError
from models.integration import RollPage, RollSummary
from services.integration_keys import utc


def window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Validate and normalize a bounded, timezone-aware history window."""
    if start.tzinfo is None or end.tzinfo is None:
        raise IntegrationError(422, "Start and end must include a timezone")
    start, end = utc(start), utc(end)
    if not start < end or end - start > timedelta(hours=24):
        raise IntegrationError(422, "Choose a window of at most 24 hours")
    return start, end


def window_id(key: dict[str, Any], start: datetime, end: datetime) -> str:
    """Bind continuation cursors to the key, channel and requested window."""
    parts = [
        str(key["_id"]),
        str(key["guild_id"]),
        str(key["channel_id"]),
        start.isoformat(),
        end.isoformat(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def read_cursor(
    cursor: str, scope: str, start: datetime, end: datetime
) -> tuple[datetime, ObjectId]:
    """Decode a continuation cursor only within its original scope and window."""
    try:
        data = json.loads(
            base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        )
        if not isinstance(data, list) or len(data) != 3 or data[0] != scope:
            raise ValueError
        date = datetime.fromisoformat(data[1])
        if date.tzinfo is None or not start <= utc(date) < end:
            raise ValueError
        return utc(date), ObjectId(data[2])
    except (ValueError, TypeError, InvalidId, binascii.Error) as err:
        raise IntegrationError(400, "Invalid cursor") from err


def summary(row: dict[str, Any]) -> RollSummary:
    """Map a stored roll to its exported fields."""
    reroll = row.get("reroll")
    return RollSummary(
        id=str(row["_id"]),
        created_at=utc(row["date"]),
        character_id=str(row["charid"]) if row.get("charid") else None,
        owner_id=str(row["user"]),
        original_outcome=row["outcome"],
        final_outcome=(reroll or {}).get("outcome", row["outcome"]),
        rerolled=reroll is not None,
        hidden=row.get("hidden") is True,
        difficulty=row.get("difficulty"),
        margin=row.get("margin"),
        impaired=row.get("impaired") is True,
        normal_dice=row.get("normal") or [],
        hunger_dice=row.get("hunger") or [],
        reroll_strategy=reroll.get("strategy") if reroll else None,
        reroll_margin=reroll.get("margin") if reroll else None,
        reroll_dice=reroll.get("dice") if reroll else None,
    )


async def history(
    key: dict[str, Any], start: datetime, end: datetime, limit: int, cursor: str | None
) -> RollPage:
    """Read a bounded page of included roll outcomes from one channel."""
    start, end = window(start, end)
    scope = window_id(key, start, end)
    query: dict[str, Any] = {
        "guild": key["guild_id"],
        "channel": key["channel_id"],
        "use_in_stats": True,
        "date": {"$gte": start, "$lt": end},
    }
    if cursor:
        date, ident = read_cursor(cursor, scope, start, end)
        query["$or"] = [{"date": {"$gt": date}}, {"date": date, "_id": {"$gt": ident}}]
    fields = {
        "date": 1,
        "charid": 1,
        "user": 1,
        "outcome": 1,
        "reroll": 1,
        "hidden": 1,
        "difficulty": 1,
        "margin": 1,
        "impaired": 1,
        "normal": 1,
        "hunger": 1,
    }
    rows = (
        await db.rolls.find(query, fields)
        .sort([("date", 1), ("_id", 1)])
        .limit(limit + 1)
        .max_time_ms(2000)
        .to_list(limit + 1)
    )
    selected = rows[:limit]
    rolls = [summary(row) for row in selected]
    next_cursor = None
    if len(rows) > limit:
        last = selected[-1]
        payload = [scope, utc(last["date"]).isoformat(), str(last["_id"])]
        next_cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return RollPage(rolls=rolls, next_cursor=next_cursor)
