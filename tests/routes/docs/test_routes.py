"""Tests for docs API routes."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient, Response

from config import settings
from routes.docs import loader
from server import app

TEST_API_KEY = "test-api-key-12345"


@pytest.fixture(autouse=True)
def mock_api_key() -> Iterator[None]:
    """Mock API_KEY for all tests."""
    with patch.object(settings, "inconnu_api_token", TEST_API_KEY):
        yield


async def get(url: str, headers: dict[str, str] | None = None, auth=True) -> Response:
    """GET a docs route, authenticated unless told otherwise."""
    headers = dict(headers or {})
    if auth:
        headers["Authorization"] = f"Bearer {TEST_API_KEY}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(url, headers=headers)


async def test_get_docs():
    """Returns the docs bundle with its version as the ETag."""
    resp = await get("/docs")
    data = resp.json()

    assert resp.status_code == 200
    assert resp.headers["ETag"] == f'"{data["version"]}"'
    assert data["version"] == loader.load(loader.DOCS_DIR).version
    assert data["nav"]
    assert any(page["path"] == "" for page in data["pages"])


async def test_get_docs_not_modified():
    """A matching If-None-Match gets a 304 with no body."""
    etag = (await get("/docs")).headers["ETag"]
    resp = await get("/docs", headers={"If-None-Match": etag})

    assert resp.status_code == 304
    assert resp.headers["ETag"] == etag
    assert resp.content == b""


async def test_get_docs_stale_etag():
    """A stale If-None-Match gets the full bundle."""
    resp = await get("/docs", headers={"If-None-Match": '"stale"'})
    assert resp.status_code == 200


async def test_get_asset():
    """Serves a docs asset with caching headers."""
    resp = await get("/docs/assets/bookmarks.png")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["Cache-Control"] == "public, max-age=86400"
    assert resp.content == (loader.DOCS_DIR / "assets" / "bookmarks.png").read_bytes()


@pytest.mark.parametrize("name", ["missing.png", "..%2FSUMMARY.md", "..%2F..%2Fpyproject.toml"])
async def test_get_asset_not_found(name: str):
    """Only files in docs/assets are served."""
    resp = await get(f"/docs/assets/{name}")
    assert resp.status_code == 404


@pytest.mark.parametrize("url", ["/docs", "/docs/assets/bookmarks.png"])
async def test_auth_required(url: str):
    """Returns 401 when no auth header is provided."""
    resp = await get(url, auth=False)
    assert resp.status_code == 401
