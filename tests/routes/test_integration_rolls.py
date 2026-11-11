"""Isolation, projection and bounded-pagination contracts for roll exports."""

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
GUILD = 323456789012345678
CHANNEL = 423456789012345678
START = datetime(2026, 6, 1, tzinfo=UTC)
END = START + timedelta(hours=1)
ROLL_FIELDS = {
    "id",
    "created_at",
    "character_id",
    "owner_id",
    "original_outcome",
    "final_outcome",
    "rerolled",
    "hidden",
    "difficulty",
    "margin",
    "impaired",
    "normal_dice",
    "hunger_dice",
    "reroll_strategy",
    "reroll_margin",
    "reroll_dice",
}


def management_headers() -> dict[str, str]:
    """Build management headers for the key owner."""
    return {"Authorization": f"Bearer {SERVICE_TOKEN}", "X-Discord-User-ID": OWNER}


def feed_headers(secret: str) -> dict[str, str]:
    """Build roll history headers for an integration key."""
    return {"Authorization": f"Bearer {SERVICE_TOKEN}", "X-Integration-Key": secret}


def window(**overrides) -> dict:
    """Build a valid history window query."""
    return {"start": START.isoformat(), "end": END.isoformat(), **overrides}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Use disposable collections and reset integration limits."""
    from services import integration_keys, integration_limits

    database = AsyncMongoMockClient(tz_aware=True).integration_roll_tests
    await database.integration_keys.create_index(
        [("owner_id", 1), ("slot", 1)],
        unique=True,
        partialFilterExpression={"active": True},
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


@pytest.fixture
async def key(client) -> dict:
    """Create a key for the test channel."""
    response = await client.post(
        "/integration-keys",
        headers=management_headers(),
        json={
            "name": "Export",
            "guild_id": str(GUILD),
            "channel_id": str(CHANNEL),
        },
    )
    assert response.status_code == 201
    return response.json()


async def insert_roll(**overrides) -> dict:
    """Insert a stored roll with private fields that must not be exported."""
    roll = {
        "_id": ObjectId(),
        "date": START + timedelta(minutes=1),
        "guild": GUILD,
        "channel": CHANNEL,
        "user": int(OWNER),
        "charid": ObjectId(),
        "outcome": "fail",
        "reroll": None,
        "hidden": False,
        "use_in_stats": True,
        "comment": "PRIVATE COMMENT",
        "raw": "PRIVATE SYNTAX",
        "pool": "PRIVATE POOL",
        "difficulty": 2,
        "margin": -1,
        "impaired": True,
        "normal": [1, 2],
        "hunger": [1],
        "message": 123,
        "name": "PRIVATE CHARACTER NAME",
        **overrides,
    }
    await db.rolls.insert_one(roll)
    return roll


async def test_feed_requires_service_auth_even_with_valid_external_key(client, key):
    """Roll history requires the service token."""
    response = await client.get(
        "/integration-rolls", headers={"X-Integration-Key": key["secret"]}, params=window()
    )
    assert response.status_code == 401


async def test_feed_requires_external_key_in_addition_to_service_auth(client):
    """Roll history requires an integration key."""
    response = await client.get("/integration-rolls", headers=management_headers(), params=window())
    assert response.status_code == 401


async def test_well_formed_invalid_credential_flood_cannot_deny_a_valid_key(client, key):
    """Failed authentication cannot exhaust valid key capacity."""
    from services.integration_limits import limits

    invalid = f"ink_{ObjectId()}_{'a' * 43}"
    for _ in range(120):
        rejected = await client.get(
            "/integration-rolls", headers=feed_headers(invalid), params=window()
        )
        assert rejected.status_code == 401
    throttled = await client.get(
        "/integration-rolls", headers=feed_headers(invalid), params=window()
    )
    assert throttled.status_code == 429
    assert "global" not in limits._buckets
    assert limits._active == 0
    assert limits._active_owners == set()
    own = await insert_roll()
    allowed = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert allowed.status_code == 200
    assert [roll["id"] for roll in allowed.json()["rolls"]] == [str(own["_id"])]
    assert limits._buckets["global"]["requests"][1] == 1


@pytest.mark.parametrize(
    "secret", ["invalid", "ink_012345678901234567890123_wrong", "", SERVICE_TOKEN]
)
async def test_invalid_external_key_is_rejected(client, secret):
    """Malformed and unknown keys are rejected."""
    response = await client.get("/integration-rolls", headers=feed_headers(secret), params=window())
    assert response.status_code == 401


async def test_external_token_is_not_an_internal_service_credential(client, key):
    """Integration keys cannot authenticate other API routes."""
    response = await client.get(
        "/characters",
        headers={"Authorization": f"Bearer {key['secret']}", "X-Discord-User-ID": OWNER},
    )
    assert response.status_code == 401


async def test_feed_scope_comes_from_key_not_forwarded_identity(client, key):
    """Results are limited to the key's guild and channel."""
    own = await insert_roll()
    await insert_roll(guild=GUILD + 1)
    await insert_roll(channel=CHANNEL + 1)
    await insert_roll(guild=None, channel=None)
    response = await client.get(
        "/integration-rolls",
        headers={**feed_headers(key["secret"]), "X-Discord-User-ID": "999999999999999999"},
        params=window(),
    )
    assert response.status_code == 200
    assert [roll["id"] for roll in response.json()["rolls"]] == [str(own["_id"])]


async def test_exact_allowlist_and_reroll_final_outcome(client, key):
    """Rolls expose only allowlisted fields and the rerolled outcome."""
    original = await insert_roll(
        reroll={"strategy": "failures", "outcome": "success", "dice": [10, 9], "margin": 1}
    )
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    assert set(response.json()) == {"rolls", "next_cursor"}
    assert response.json()["next_cursor"] is None
    exported = response.json()["rolls"][0]
    assert set(exported) == ROLL_FIELDS
    assert exported["id"] == str(original["_id"])
    assert exported["character_id"] == str(original["charid"])
    assert exported["owner_id"] == OWNER
    assert exported["original_outcome"] == "fail"
    assert exported["final_outcome"] == "success"
    assert exported["rerolled"] is True
    assert exported["hidden"] is False
    assert exported["difficulty"] == 2
    assert exported["margin"] == -1
    assert exported["impaired"] is True
    assert exported["normal_dice"] == [1, 2]
    assert exported["hunger_dice"] == [1]
    assert exported["reroll_strategy"] == "failures"
    assert exported["reroll_margin"] == 1
    assert exported["reroll_dice"] == [10, 9]
    assert "PRIVATE" not in response.text


@pytest.mark.parametrize(
    "outcome", ["critical", "messy", "success", "fail", "total_fail", "bestial"]
)
async def test_non_rerolled_outcome_and_optional_character(client, key, outcome):
    """Rolls without a reroll or character are exported correctly."""
    await insert_roll(outcome=outcome, charid=None)
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    exported = response.json()["rolls"][0]
    assert exported["character_id"] is None
    assert exported["original_outcome"] == exported["final_outcome"] == outcome
    assert exported["rerolled"] is False
    assert exported["reroll_strategy"] is None
    assert exported["reroll_margin"] is None
    assert exported["reroll_dice"] is None


async def test_legacy_missing_mechanics_use_empty_values(client, key):
    """Rolls without mechanics fields are exported with empty values."""
    roll = await insert_roll()
    await db.rolls.update_one(
        {"_id": roll["_id"]},
        {"$unset": {"difficulty": "", "margin": "", "impaired": "", "normal": "", "hunger": ""}},
    )
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    exported = response.json()["rolls"][0]
    assert exported["difficulty"] is None
    assert exported["margin"] is None
    assert exported["impaired"] is False
    assert exported["normal_dice"] == []
    assert exported["hunger_dice"] == []


@pytest.mark.parametrize("hidden,expected", [(True, True), (False, False), (None, False)])
async def test_hidden_flag_is_exported(client, key, hidden, expected):
    """Hidden rolls are exported with their hidden flag."""
    await insert_roll(hidden=hidden)
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    assert [roll["hidden"] for roll in response.json()["rolls"]] == [expected]


@pytest.mark.parametrize("included", [False, None])
async def test_excluded_rolls_are_not_exported(client, key, included):
    """Rolls excluded from statistics are omitted."""
    await insert_roll(use_in_stats=included)
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    assert response.json()["rolls"] == []


async def test_legacy_missing_stats_flag_is_excluded(client, key):
    """Rolls without a statistics flag are omitted."""
    roll = await insert_roll()
    await db.rolls.update_one({"_id": roll["_id"]}, {"$unset": {"use_in_stats": ""}})
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    assert response.json()["rolls"] == []


async def test_range_is_start_inclusive_end_exclusive(client, key):
    """The window includes its start and excludes its end."""
    inside = await insert_roll(date=START)
    await insert_roll(date=START - timedelta(milliseconds=1))
    await insert_roll(date=END)
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 200
    assert [roll["id"] for roll in response.json()["rolls"]] == [str(inside["_id"])]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"start": START.isoformat()},
        window(end=START.isoformat()),
        window(end=(START - timedelta(seconds=1)).isoformat()),
        window(end=(START + timedelta(hours=24, seconds=1)).isoformat()),
        window(start="2026-06-01T00:00:00"),
        window(limit=0),
        window(limit=101),
        window(limit="1.5"),
        window(start="not-a-date"),
    ],
)
async def test_invalid_or_unbounded_query_is_rejected(client, key, params):
    """Invalid or unbounded windows are rejected."""
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=params
    )
    assert response.status_code == 422


async def test_same_timestamp_keyset_pagination_has_no_duplicates_or_omissions(client, key):
    """Pagination is stable for rolls with equal timestamps."""
    records = [await insert_roll() for _ in range(5)]
    seen = []
    cursor = None
    for _ in range(4):
        params = window(limit=2)
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get(
            "/integration-rolls", headers=feed_headers(key["secret"]), params=params
        )
        assert response.status_code == 200
        assert len(response.json()["rolls"]) <= 2
        seen.extend(roll["id"] for roll in response.json()["rolls"])
        cursor = response.json()["next_cursor"]
        if cursor is None:
            break
    assert cursor is None
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == {str(roll["_id"]) for roll in records}


async def test_cursor_cannot_be_reused_for_a_different_window(client, key):
    """A cursor is valid only for its original window."""
    for _ in range(2):
        await insert_roll()
    first = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window(limit=1)
    )
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor
    response = await client.get(
        "/integration-rolls",
        headers=feed_headers(key["secret"]),
        params=window(end=(END + timedelta(hours=1)).isoformat(), cursor=cursor),
    )
    assert response.status_code == 400


async def test_malformed_cursor_is_rejected(client, key):
    """Malformed cursors are rejected."""
    response = await client.get(
        "/integration-rolls",
        headers=feed_headers(key["secret"]),
        params=window(cursor="not-a-cursor"),
    )
    assert response.status_code == 400


async def test_revoked_key_is_rejected_on_next_request(client, key):
    """Revoked keys are rejected immediately."""
    revoked = await client.post(
        f"/integration-keys/{key['key']['id']}/revoke", headers=management_headers()
    )
    assert revoked.status_code == 200
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 401


async def test_expired_key_is_rejected_on_next_request(client, key):
    """Expired keys are rejected immediately."""
    await db.integration_keys.update_one(
        {"_id": ObjectId(key["key"]["id"])},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )
    response = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert response.status_code == 401


async def test_missing_expiry_fails_closed(client, key):
    """Keys without an expiry field are rejected."""
    await db.integration_keys.update_one(
        {"_id": ObjectId(key["key"]["id"])},
        {"$unset": {"expires_at": ""}},
    )
    response = await client.get(
        "/integration-rolls",
        headers=feed_headers(key["secret"]),
        params=window(),
    )
    assert response.status_code == 401


async def test_non_expiring_key_still_requires_current_permissions_and_revocation(client):
    """Non-expiring keys still require permissions and can be revoked."""
    from services import integration_keys

    created = await client.post(
        "/integration-keys",
        headers=management_headers(),
        json={
            "name": "Permanent export",
            "guild_id": str(GUILD),
            "channel_id": str(CHANNEL),
            "expires_in_days": None,
        },
    )
    assert created.status_code == 201
    key = created.json()
    await insert_roll()
    response = await client.get(
        "/integration-rolls",
        headers=feed_headers(key["secret"]),
        params=window(),
    )
    assert response.status_code == 200
    assert len(response.json()["rolls"]) == 1
    with patch.object(
        integration_keys,
        "authorize_channel",
        AsyncMock(side_effect=IntegrationError(403, "Channel access denied")),
    ):
        denied = await client.get(
            "/integration-rolls",
            headers=feed_headers(key["secret"]),
            params=window(),
        )
    assert denied.status_code == 403
    revoked = await client.post(
        f"/integration-keys/{key['key']['id']}/revoke",
        headers=management_headers(),
    )
    assert revoked.status_code == 200
    rejected = await client.get(
        "/integration-rolls",
        headers=feed_headers(key["secret"]),
        params=window(),
    )
    assert rejected.status_code == 401


async def test_feed_rechecks_current_channel_authorization(client, key):
    """Each request rechecks channel authorization."""
    from services import integration_keys

    with patch.object(
        integration_keys,
        "authorize_channel",
        new=AsyncMock(side_effect=IntegrationError(403, "Channel access denied")),
    ):
        response = await client.get(
            "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
        )
    assert response.status_code == 403


async def test_subsequent_query_reflects_reroll_and_exclusion(client, key):
    """Results reflect later rerolls and exclusions."""
    roll = await insert_roll()
    await db.rolls.update_one({"_id": roll["_id"]}, {"$set": {"reroll": {"outcome": "critical"}}})
    rerolled = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert rerolled.status_code == 200
    assert rerolled.json()["rolls"][0]["final_outcome"] == "critical"
    await db.rolls.update_one({"_id": roll["_id"]}, {"$set": {"use_in_stats": False}})
    excluded = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window()
    )
    assert excluded.status_code == 200
    assert excluded.json()["rolls"] == []


async def test_known_key_id_with_wrong_secret_is_rejected(client, key):
    """A known key ID with the wrong secret is rejected."""
    wrong_secret = f"ink_{key['key']['id']}_{'A' * 43}"
    response = await client.get(
        "/integration-rolls", headers=feed_headers(wrong_secret), params=window()
    )
    assert response.status_code == 401


async def test_cursor_cannot_cross_channel_scope(client, key):
    """A cursor cannot be used with another channel's key."""
    for _ in range(2):
        await insert_roll()
    first = await client.get(
        "/integration-rolls", headers=feed_headers(key["secret"]), params=window(limit=1)
    )
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor
    other = await client.post(
        "/integration-keys",
        headers=management_headers(),
        json={
            "name": "Other channel",
            "guild_id": str(GUILD),
            "channel_id": str(CHANNEL + 1),
        },
    )
    assert other.status_code == 201
    response = await client.get(
        "/integration-rolls",
        headers=feed_headers(other.json()["secret"]),
        params=window(cursor=cursor),
    )
    assert response.status_code == 400
