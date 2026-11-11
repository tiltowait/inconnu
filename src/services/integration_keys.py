"""Scoped integration credentials."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from bson import ObjectId
from loguru import logger
from pymongo.errors import DuplicateKeyError

import db
from errors import IntegrationError
from models import VGuild
from models.integration import ChannelChoice, CreatedKey, KeyRequest, KeySummary
from services.integration_access import authorize_channel, eligible

if TYPE_CHECKING:
    from bot import InconnuBot

TOKEN = re.compile(r"ink_([0-9a-f]{24})_[A-Za-z0-9_-]{43}\Z")


def utc(value: datetime) -> datetime:
    """Normalize database timestamps to UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def summary(row: dict[str, Any]) -> KeySummary:
    """Expose key metadata without authentication material."""
    return KeySummary(
        id=str(row["_id"]),
        name=row["name"],
        prefix=row["prefix"],
        guild_id=str(row["guild_id"]),
        channel_id=str(row["channel_id"]),
        created_at=utc(row["created_at"]),
        expires_at=utc(row["expires_at"]) if row["expires_at"] is not None else None,
        revoked_at=utc(row["revoked_at"]) if row.get("revoked_at") else None,
    )


async def list_keys(owner_id: int) -> list[KeySummary]:
    """List only the owner's keys, preserving visibility of active keys."""
    rows = (
        await db.integration_keys.find({"owner_id": owner_id})
        .sort([("active", -1), ("created_at", -1), ("_id", -1)])
        .limit(100)
        .to_list(100)
    )
    return [summary(row) for row in rows]


async def channel_choices(bot: InconnuBot, owner_id: int) -> list[ChannelChoice]:
    """Offer cached eligible channels; creation checks fresh permissions."""
    if not bot.is_ready() or bot.is_closed():
        return []
    choices = []
    for guild in bot.guilds:
        member = guild.get_member(owner_id)
        if member is None:
            continue
        config = await VGuild.find_one({"guild": guild.id})
        role = config.settings.storyteller_role if config else None
        for channel in guild.text_channels:
            if eligible(member, channel, role):
                choices.append(
                    ChannelChoice(
                        guild_id=str(guild.id),
                        guild_name=guild.name,
                        channel_id=str(channel.id),
                        channel_name=channel.name,
                    )
                )
    return choices


async def create_key(bot: InconnuBot, owner_id: int, data: KeyRequest) -> CreatedKey:
    """Create a scoped key once per form submission within the atomic owner cap."""
    creation = (
        {"owner_id": owner_id, "creation_id": str(data.creation_id)}
        if data.creation_id is not None
        else None
    )
    if creation and await db.integration_keys.find_one(creation, {"_id": 1}):
        raise IntegrationError(
            409, "This key request was already used. Reload to create another key."
        )
    await authorize_channel(bot, owner_id, int(data.guild_id), int(data.channel_id))
    now = datetime.now(UTC)
    now = now.replace(microsecond=now.microsecond // 1000 * 1000)
    await db.integration_keys.update_many(
        {"owner_id": owner_id, "active": True, "expires_at": {"$ne": None, "$lte": now}},
        {"$set": {"active": False}},
    )
    for _ in range(5):
        occupied = (
            await db.integration_keys.find({"owner_id": owner_id, "active": True}, {"slot": 1})
            .limit(5)
            .to_list(5)
        )
        free = set(range(5)) - {row["slot"] for row in occupied}
        if not free:
            raise IntegrationError(409, "At most five active API keys are allowed")
        ident = ObjectId()
        secret = f"ink_{ident}_{secrets.token_urlsafe(32)}"
        row = {
            "_id": ident,
            "owner_id": owner_id,
            "name": data.name,
            "guild_id": int(data.guild_id),
            "channel_id": int(data.channel_id),
            "scope": "rolls:read",
            "prefix": f"ink_{str(ident)[:8]}",
            "digest": hashlib.sha256(secret.encode()).hexdigest(),
            "created_at": now,
            "expires_at": now + timedelta(days=data.expires_in_days)
            if data.expires_in_days is not None
            else None,
            "revoked_at": None,
            "active": True,
            "slot": min(free),
        }
        if creation:
            row["creation_id"] = creation["creation_id"]
        try:
            await db.integration_keys.insert_one(row)
        except DuplicateKeyError:
            if creation and await db.integration_keys.find_one(creation, {"_id": 1}):
                raise IntegrationError(
                    409, "This key request was already used. Reload to create another key."
                ) from None
            continue
        logger.info("Created integration key {} for user {}", ident, owner_id)
        return CreatedKey(key=summary(row), secret=secret)
    raise IntegrationError(409, "API keys changed; try again")


async def revoke_key(owner_id: int, key_id: str) -> KeySummary:
    """Revoke an owned key even when its original channel is inaccessible."""
    if not re.fullmatch(r"[0-9a-f]{24}", key_id):
        raise IntegrationError(404, "API key not found")
    row = await db.integration_keys.find_one({"_id": ObjectId(key_id), "owner_id": owner_id})
    if row is None:
        raise IntegrationError(404, "API key not found")
    if row.get("revoked_at") is None:
        now = datetime.now(UTC)
        row["revoked_at"] = now.replace(microsecond=now.microsecond // 1000 * 1000)
        await db.integration_keys.update_one(
            {"_id": row["_id"], "owner_id": owner_id, "revoked_at": None},
            {"$set": {"revoked_at": row["revoked_at"], "active": False}},
        )
        logger.info("Revoked integration key {} for user {}", key_id, owner_id)
    return summary(row)


async def authenticate(secret: str | None) -> dict[str, Any]:
    """Verify a stored digest, scope, expiry and revocation by indexed key ID."""
    match = TOKEN.fullmatch(secret or "")
    if match is None:
        raise IntegrationError(401, "Invalid API key")
    row = await db.integration_keys.find_one({"_id": ObjectId(match[1])})
    digest = hashlib.sha256(secret.encode()).hexdigest()
    if row is None or not hmac.compare_digest(row.get("digest", ""), digest):
        raise IntegrationError(401, "Invalid API key")
    if (
        row.get("scope") != "rolls:read"
        or row.get("active") is not True
        or row.get("revoked_at") is not None
        or "expires_at" not in row
        or (row["expires_at"] is not None and utc(row["expires_at"]) <= datetime.now(UTC))
    ):
        raise IntegrationError(401, "Invalid API key")
    return row
