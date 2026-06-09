"""Tests for web API authentication utilities."""

from unittest.mock import patch

import pytest
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from config import settings
from routes.auth import verify_api_key

TEST_API_KEY = "test-api-key-12345"


@pytest.fixture(autouse=True)
def mock_api_key():
    """Pin the configured API token for each test."""
    with patch.object(settings, "inconnu_api_token", TEST_API_KEY):
        yield


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    """Build bearer credentials carrying the given token."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_verify_api_key_accepts_valid_token():
    """A matching token passes and the credentials are returned unchanged."""
    creds = _credentials(TEST_API_KEY)
    assert await verify_api_key(creds) is creds


async def test_verify_api_key_rejects_invalid_token():
    """A non-matching token raises a 401."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(_credentials("wrong-token"))
    assert exc_info.value.status_code == 401


async def test_verify_api_key_rejects_token_prefix():
    """A token that is a prefix of the real one is still rejected.

    Guards against a comparison that short-circuits on length or first
    mismatch in a way that would accept partial matches."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(_credentials(TEST_API_KEY[:-1]))
    assert exc_info.value.status_code == 401
