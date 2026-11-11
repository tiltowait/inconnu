"""Security and lifecycle contracts for website-managed roll export keys."""

import hashlib
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import db
from config import settings
from errors import IntegrationError
from server import app

SERVICE_TOKEN = "test-integration-service-token"
OWNER = "123456789012345678"
OTHER_OWNER = "223456789012345678"
GUILD = "323456789012345678"
CHANNEL = "423456789012345678"
SUMMARY_FIELDS = {
    "id",
    "name",
    "prefix",
    "guild_id",
    "channel_id",
    "created_at",
    "expires_at",
    "revoked_at",
    "scope",
}


def headers(owner: str = OWNER) -> dict[str, str]:
    """Build management headers for an authenticated website user."""
    return {"Authorization": f"Bearer {SERVICE_TOKEN}", "X-Discord-User-ID": owner}


def key_body(**overrides) -> dict:
    """Build a valid key creation request."""
    return {"name": "Campaign export", "guild_id": GUILD, "channel_id": CHANNEL, **overrides}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Use disposable raw collections; never inherit a configured Mongo connection."""
    from services import integration_keys, integration_limits

    database = AsyncMongoMockClient(tz_aware=True).integration_tests
    await database.integration_keys.create_index(
        [("owner_id", 1), ("slot", 1)],
        unique=True,
        partialFilterExpression={"active": True},
    )
    await database.integration_keys.create_index(
        [("owner_id", 1), ("creation_id", 1)],
        unique=True,
        partialFilterExpression={"creation_id": {"$type": "string"}},
    )
    with (
        patch.object(settings, "inconnu_api_token", SERVICE_TOKEN),
        patch.object(db, "integration_keys", database.integration_keys, create=True),
        patch.object(db, "rolls", database.rolls),
        patch.object(integration_keys, "authorize_channel", new=AsyncMock()),
        patch.object(integration_keys, "channel_choices", new=AsyncMock(return_value=[])),
        patch.object(integration_limits.limits, "_buckets", {}),
        patch.object(integration_limits.limits, "_active", 0),
        patch.object(integration_limits.limits, "_active_owners", set()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield http


async def create_key(client: AsyncClient, **overrides) -> dict:
    """Create a key and return the creation response."""
    response = await client.post("/integration-keys", headers=headers(), json=key_body(**overrides))
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/integration-keys"),
        ("POST", "/integration-keys"),
        ("POST", "/integration-keys/012345678901234567890123/revoke"),
    ],
)
async def test_management_requires_service_auth(client, method, path):
    """Management routes reject requests without the service token."""
    response = await client.request(
        method, path, headers={"X-Discord-User-ID": OWNER}, json=key_body()
    )
    assert response.status_code == 401


async def test_management_requires_forwarded_identity(client):
    """Management routes require the forwarded Discord user ID."""
    response = await client.get(
        "/integration-keys", headers={"Authorization": f"Bearer {SERVICE_TOKEN}"}
    )
    assert response.status_code == 400


async def test_key_creation_returns_secret_only_once_and_stores_no_plaintext(client):
    """Creation returns the secret once and stores only its digest."""
    created = await create_key(client)
    assert set(created) == {"key", "secret"}
    summary = created["key"]
    assert set(summary) == SUMMARY_FIELDS
    assert summary["scope"] == "rolls:read"
    assert summary["guild_id"] == GUILD
    assert summary["channel_id"] == CHANNEL
    assert summary["revoked_at"] is None
    assert created["secret"].startswith(f"ink_{summary['id']}_")
    assert re.fullmatch(r"ink_[0-9a-f]{24}_[A-Za-z0-9_-]{43}", created["secret"])
    stored = await db.integration_keys.find_one({"_id": ObjectId(summary["id"])})
    assert stored is not None
    assert created["secret"] not in repr(stored)
    assert stored["digest"] == hashlib.sha256(created["secret"].encode()).hexdigest()
    assert created["secret"] not in repr(summary)
    expires = datetime.fromisoformat(summary["expires_at"])
    created_at = datetime.fromisoformat(summary["created_at"])
    assert expires - created_at == timedelta(days=90)
    listed = await client.get("/integration-keys", headers=headers())
    assert listed.status_code == 200
    assert listed.headers["Cache-Control"] == "no-store"
    assert set(listed.json()) == {"keys", "channels"}
    assert listed.json()["keys"] == [summary]
    assert created["secret"] not in listed.text
    assert set(listed.json()["keys"][0]) == SUMMARY_FIELDS


async def test_list_only_returns_callers_keys(client):
    """Listing excludes other accounts' keys."""
    created = await create_key(client)
    response = await client.get("/integration-keys", headers=headers(OTHER_OWNER))
    assert response.status_code == 200
    assert response.json()["keys"] == []
    assert created["key"]["id"] not in response.text


async def test_foreign_owner_cannot_revoke_key(client):
    """Another account cannot revoke a key."""
    created = await create_key(client)
    response = await client.post(
        f"/integration-keys/{created['key']['id']}/revoke", headers=headers(OTHER_OWNER)
    )
    assert response.status_code == 404
    listed = await client.get("/integration-keys", headers=headers())
    assert listed.status_code == 200
    assert listed.headers["Cache-Control"] == "no-store"
    assert listed.json()["keys"][0]["revoked_at"] is None


async def test_owner_can_revoke_after_losing_channel_access(client):
    """Revocation does not depend on current channel access."""
    from services import integration_keys

    created = await create_key(client)
    with patch.object(
        integration_keys,
        "authorize_channel",
        new=AsyncMock(side_effect=IntegrationError(403, "Channel access denied")),
    ):
        response = await client.post(
            f"/integration-keys/{created['key']['id']}/revoke", headers=headers()
        )
    assert response.status_code == 200
    assert set(response.json()) == {"key"}
    assert set(response.json()["key"]) == SUMMARY_FIELDS
    assert response.json()["key"]["revoked_at"] is not None
    assert created["secret"] not in response.text


@pytest.mark.parametrize("days", [0, -1, 91, 1.5, True])
async def test_expiry_outside_contract_is_rejected(client, days):
    """Expiry must be a whole number of days from 1 to 90."""
    response = await client.post(
        "/integration-keys", headers=headers(), json=key_body(expires_in_days=days)
    )
    assert response.status_code == 422
    assert await db.integration_keys.count_documents({}) == 0


@pytest.mark.parametrize(
    "extra", [{"scope": "characters:read"}, {"owner_id": OTHER_OWNER}, {"secret": "chosen"}]
)
async def test_unrecognized_privilege_or_secret_fields_are_rejected(client, extra):
    """Creation rejects caller-supplied scope, owner or secret fields."""
    response = await client.post("/integration-keys", headers=headers(), json=key_body(**extra))
    assert response.status_code == 422
    assert await db.integration_keys.count_documents({}) == 0


async def test_create_requires_current_channel_authorization(client):
    """Creation fails when channel authorization fails."""
    from services import integration_keys

    with patch.object(
        integration_keys,
        "authorize_channel",
        new=AsyncMock(side_effect=IntegrationError(403, "Channel access denied")),
    ):
        response = await client.post("/integration-keys", headers=headers(), json=key_body())
    assert response.status_code == 403
    assert await db.integration_keys.count_documents({}) == 0


async def test_active_key_cap_and_revocation_releases_slot(client):
    """The five-key cap applies and revocation frees a slot."""
    keys = [await create_key(client, name=f"Export {index}") for index in range(5)]
    from services.integration_limits import limits

    limits._buckets.clear()
    response = await client.post("/integration-keys", headers=headers(), json=key_body())
    assert response.status_code == 409
    limits._buckets.clear()
    revoked = await client.post(
        f"/integration-keys/{keys[0]['key']['id']}/revoke", headers=headers()
    )
    assert revoked.status_code == 200
    await create_key(client)


async def test_expired_key_does_not_consume_active_slot(client):
    """Expired keys do not count toward the cap."""
    from services.integration_limits import limits

    await create_key(client)
    await db.integration_keys.update_many(
        {}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}}
    )
    limits._buckets.clear()
    for index in range(5):
        await create_key(client, name=f"New export {index}")


@pytest.mark.parametrize(
    "invalid",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 65},
        {"guild_id": "0"},
        {"guild_id": str(2**64)},
        {"guild_id": int(GUILD)},
        {"channel_id": "not-a-channel"},
        {"channel_id": str(2**64)},
    ],
)
async def test_invalid_name_or_scope_ids_are_rejected(client, invalid):
    """Creation rejects invalid names and Discord IDs."""
    response = await client.post("/integration-keys", headers=headers(), json=key_body(**invalid))
    assert response.status_code == 422
    assert await db.integration_keys.count_documents({}) == 0


async def test_shorter_key_expiry_is_honored(client):
    """A shorter requested expiry is stored."""
    created = await create_key(client, expires_in_days=1)
    summary = created["key"]
    expires = datetime.fromisoformat(summary["expires_at"])
    created_at = datetime.fromisoformat(summary["created_at"])
    assert expires - created_at == timedelta(days=1)


async def test_explicit_non_expiring_key_has_null_expiry(client):
    """A key created without expiry stores and lists a null expiry."""
    created = await create_key(client, expires_in_days=None)
    assert created["key"]["expires_at"] is None
    stored = await db.integration_keys.find_one({"_id": ObjectId(created["key"]["id"])})
    assert stored["expires_at"] is None
    listed = await client.get("/integration-keys", headers=headers())
    assert listed.status_code == 200
    assert listed.json()["keys"][0]["expires_at"] is None
    assert created["secret"] not in listed.text


async def test_non_expiring_key_keeps_its_slot_during_expired_key_cleanup(client):
    """Expired key cleanup does not release non-expiring keys."""
    from services.integration_limits import limits

    permanent = await create_key(client, expires_in_days=None)
    for index in range(4):
        await create_key(client, name=f"Old export {index}")
    await db.integration_keys.update_many(
        {"expires_at": {"$ne": None}},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )
    limits._buckets.clear()
    for index in range(4):
        await create_key(client, name=f"New export {index}")
    stored = await db.integration_keys.find_one({"_id": ObjectId(permanent["key"]["id"])})
    assert stored["active"] is True
    assert stored["expires_at"] is None
    assert await db.integration_keys.count_documents({"active": True}) == 5
    response = await client.post("/integration-keys", headers=headers(), json=key_body())
    assert response.status_code == 409


async def test_active_key_remains_visible_after_one_hundred_newer_revocations(client):
    """Active keys are listed before revoked keys."""
    created = await create_key(client)
    active = await db.integration_keys.find_one({"_id": ObjectId(created["key"]["id"])})
    assert active is not None
    revoked_at = datetime.now(UTC)
    await db.integration_keys.insert_many(
        [
            {
                **active,
                "_id": ObjectId(),
                "active": False,
                "revoked_at": revoked_at,
                "created_at": revoked_at + timedelta(seconds=index + 1),
            }
            for index in range(100)
        ]
    )
    response = await client.get("/integration-keys", headers=headers())
    assert response.status_code == 200
    assert created["key"]["id"] in {key["id"] for key in response.json()["keys"]}
    assert len(response.json()["keys"]) <= 100


async def test_public_request_exhaustion_cannot_block_owner_revocation(client):
    """Failed roll requests cannot block revocation."""
    created = await create_key(client)
    start = datetime.now(UTC)
    params = {"start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat()}
    invalid = f"ink_{ObjectId()}_{'a' * 43}"
    for _ in range(120):
        await client.get(
            "/integration-rolls",
            params=params,
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}", "X-Integration-Key": invalid},
        )
    exhausted = await client.get(
        "/integration-rolls",
        params=params,
        headers={"Authorization": f"Bearer {SERVICE_TOKEN}", "X-Integration-Key": invalid},
    )
    assert exhausted.status_code == 429
    response = await client.post(
        f"/integration-keys/{created['key']['id']}/revoke",
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["key"]["revoked_at"] is not None


async def test_public_concurrency_cannot_block_owner_revocation(client):
    """Roll request concurrency cannot block revocation."""
    from contextlib import AsyncExitStack

    from services import integration_limits

    created = await create_key(client)
    async with AsyncExitStack() as stack:
        for index in range(4):
            await stack.enter_async_context(
                integration_limits.limits.admit_request(str(index), index)
            )
        response = await client.post(
            f"/integration-keys/{created['key']['id']}/revoke",
            headers=headers(),
        )
    assert response.status_code == 200
    assert response.json()["key"]["revoked_at"] is not None


async def test_public_owner_quota_cannot_block_owner_revocation(client):
    """An exhausted roll quota cannot block revocation."""
    from services import integration_limits

    created = await create_key(client)
    for index in range(60):
        async with integration_limits.limits.admit_request(f"key:{index}", int(OWNER)):
            pass
    response = await client.post(
        f"/integration-keys/{created['key']['id']}/revoke",
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["key"]["revoked_at"] is not None


async def test_management_exhaustion_for_one_account_does_not_block_another_revoke(client):
    """Management limits apply per account."""
    created = await create_key(client)
    other = await client.post("/integration-keys", headers=headers(OTHER_OWNER), json=key_body())
    assert other.status_code == 201
    for _ in range(29):
        listed = await client.get("/integration-keys", headers=headers())
        assert listed.status_code == 200
    exhausted = await client.get("/integration-keys", headers=headers())
    assert exhausted.status_code == 429
    revoked = await client.post(
        f"/integration-keys/{other.json()['key']['id']}/revoke", headers=headers(OTHER_OWNER)
    )
    assert revoked.status_code == 200
    assert revoked.json()["key"]["revoked_at"] is not None
    assert created["key"]["id"] != revoked.json()["key"]["id"]


async def test_repeated_creation_identifier_never_creates_an_additional_key(client):
    """A repeated creation ID does not create another key."""
    from uuid import uuid4

    creation_id = str(uuid4())
    created = await create_key(client, creation_id=creation_id)
    repeated = await client.post(
        "/integration-keys", headers=headers(), json=key_body(creation_id=creation_id)
    )
    assert repeated.status_code == 409
    assert created["secret"] not in repeated.text
    assert await db.integration_keys.count_documents({"owner_id": int(OWNER)}) == 1
