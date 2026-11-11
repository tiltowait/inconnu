"""Authenticated admission remains independent of failures and account management."""

import asyncio
from contextlib import AsyncExitStack
from unittest.mock import patch

import pytest

from errors import IntegrationError
from services.integration_limits import IntegrationLimits


async def test_key_limit_and_retry_after():
    limits = IntegrationLimits()
    with patch("services.integration_limits.time.monotonic", return_value=100):
        for _ in range(30):
            async with limits.admit_request("stored-key-id", 1):
                pass
        with pytest.raises(IntegrationError) as exc:
            async with limits.admit_request("stored-key-id", 1):
                pytest.fail("Exhausted key should be rejected")
    assert exc.value.status == 429
    assert exc.value.retry_after == 60
    assert limits._buckets["global"]["requests"][1] == 30


async def test_owner_limit_spans_keys_without_charging_global_on_rejection():
    limits = IntegrationLimits()
    for i in range(60):
        async with limits.admit_request(str(i % 3), 1):
            pass
    with pytest.raises(IntegrationError) as exc:
        async with limits.admit_request("another-key", 1):
            pytest.fail("Exhausted owner should be rejected")
    assert exc.value.status == 429
    assert limits._buckets["global"]["requests"][1] == 60
    async with limits.admit_request("unrelated-owner-key", 2):
        pass


def test_expired_buckets_release_capacity():
    limits = IntegrationLimits()
    with patch("services.integration_limits.time.monotonic", return_value=100):
        for _ in range(5):
            limits.check_create_rate_limit(1)
        with pytest.raises(IntegrationError) as exc:
            limits.check_create_rate_limit(1)
        assert exc.value.status == 429
    with patch("services.integration_limits.time.monotonic", return_value=160):
        limits.check_create_rate_limit(1)
    assert limits._buckets == {"create": {"1": (220, 1)}}


def test_category_capacity_never_evicts_live_limits_or_blocks_management():
    limits = IntegrationLimits()
    with patch("services.integration_limits.MAX_BUCKETS", 2):
        limits.check_create_rate_limit(1)
        limits.check_create_rate_limit(2)
        with pytest.raises(IntegrationError) as exc:
            limits.check_create_rate_limit(3)
        limits.check_management_rate_limit(3)
    assert exc.value.status == 429
    assert len(limits._buckets["create"]) == 2
    assert "1" in limits._buckets["create"]


async def test_failed_authentication_does_not_consume_authenticated_admission():
    limits = IntegrationLimits()
    for _ in range(120):
        limits.failed_authentication()
    with pytest.raises(IntegrationError) as exc:
        limits.failed_authentication()
    assert exc.value.status == 429
    async with limits.admit_request("valid-key", 1):
        assert limits._active == 1
    assert limits._buckets["global"]["requests"][1] == 1


async def test_authenticated_global_limit_spans_distinct_accounts():
    limits = IntegrationLimits()
    for owner in range(120):
        async with limits.admit_request(str(owner), owner):
            pass
    with pytest.raises(IntegrationError) as exc:
        async with limits.admit_request("new-key", 121):
            pytest.fail("Authenticated global limit should be enforced")
    assert exc.value.status == 429
    limits.check_management_rate_limit(121)
    assert limits._active == 0


async def test_concurrency_rejects_without_waiting_and_recovers():
    limits = IntegrationLimits()
    async with AsyncExitStack() as stack:
        for owner in range(4):
            await stack.enter_async_context(limits.admit_request(str(owner), owner))
        with pytest.raises(IntegrationError) as exc:
            async with limits.admit_request("fifth-key", 5):
                pytest.fail("Request should not wait in a queue")
        assert exc.value.status == 429
        assert exc.value.retry_after == 1
    assert limits._active == 0
    assert limits._active_owners == set()
    async with limits.admit_request("fifth-key", 5):
        assert limits._active == 1


async def test_one_owner_cannot_hold_multiple_concurrency_slots():
    limits = IntegrationLimits()
    async with limits.admit_request("first-key", 1):
        with pytest.raises(IntegrationError) as exc:
            async with limits.admit_request("second-key", 1):
                pytest.fail("One owner may occupy only one slot")
        assert exc.value.status == 429
        async with limits.admit_request("another-owner", 2):
            assert limits._active == 2
    assert limits._buckets["global"]["requests"][1] == 2


async def test_admission_released_when_work_fails():
    limits = IntegrationLimits()
    with pytest.raises(ValueError):
        async with limits.admit_request("key", 1):
            raise ValueError("Downstream failure")
    assert limits._active == 0
    assert limits._active_owners == set()
    async with limits.admit_request("key", 1):
        pass


async def test_admission_released_on_task_cancellation():
    limits = IntegrationLimits()
    entered = asyncio.Event()

    async def work():
        async with limits.admit_request("key", 1):
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(work())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert limits._active == 0
    assert limits._active_owners == set()
    async with limits.admit_request("key", 1):
        pass
