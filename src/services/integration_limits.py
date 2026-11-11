"""Bounded admission for integrations; requires one backend process."""

import math
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from errors import IntegrationError

WINDOW = 60
MAX_BUCKETS = 2048
GLOBAL_LIMIT = 120
FAILED_AUTH_LIMIT = 120
CONCURRENT_LIMIT = 4
KEY_LIMIT = 30
OWNER_LIMIT = 60
CREATE_LIMIT = 5
MANAGEMENT_LIMIT = 30


class IntegrationLimits:
    """Keep independent bounded windows for roll access, failures and management."""

    def __init__(self) -> None:
        """Initialize rate windows and authenticated request occupancy."""
        self._buckets: dict[str, dict[str, tuple[float, int]]] = {}
        self._active = 0
        self._active_owners: set[int] = set()

    def _consume(self, category: str, identity: str, limit: int, *, charge: bool = True) -> None:
        """Check, and optionally charge, one category without evicting other categories."""
        now = time.monotonic()
        buckets = {
            key: bucket
            for key, bucket in self._buckets.get(category, {}).items()
            if bucket[0] > now
        }
        self._buckets[category] = buckets
        expires, count = buckets.get(identity, (now + WINDOW, 0))
        if count >= limit:
            self._reject(expires - now)
        if identity not in buckets and len(buckets) >= MAX_BUCKETS:
            self._reject(min(bucket[0] for bucket in buckets.values()) - now)
        if charge:
            buckets[identity] = (expires, count + 1)

    @staticmethod
    def _reject(retry_after: float) -> None:
        """Reject immediately with the next useful retry time."""
        raise IntegrationError(
            429, "Integration request limit exceeded", max(1, math.ceil(retry_after))
        )

    def failed_authentication(self) -> None:
        """Charge rejected credentials without affecting authenticated requests."""
        self._consume("failed", "requests", FAILED_AUTH_LIMIT)

    @asynccontextmanager
    async def admit_request(self, key_id: str, owner_id: int) -> AsyncIterator[None]:
        """Admit an authenticated owner after shared capacity, rate and concurrency checks."""
        if owner_id in self._active_owners or self._active >= CONCURRENT_LIMIT:
            self._reject(1)
        self._consume("global", "requests", GLOBAL_LIMIT, charge=False)
        self._consume("owner", str(owner_id), OWNER_LIMIT)
        self._consume("key", key_id, KEY_LIMIT)
        self._consume("global", "requests", GLOBAL_LIMIT)
        self._active += 1
        self._active_owners.add(owner_id)
        try:
            yield
        finally:
            self._active -= 1
            self._active_owners.remove(owner_id)

    def check_management_rate_limit(self, owner_id: int) -> None:
        """Limit management per authenticated account without a shared admission pool."""
        self._consume("management", str(owner_id), MANAGEMENT_LIMIT)

    def check_create_rate_limit(self, owner_id: int) -> None:
        """Apply the additional per-account key creation limit."""
        self._consume("create", str(owner_id), CREATE_LIMIT)


limits = IntegrationLimits()
