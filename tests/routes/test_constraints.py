"""Tests for the constraints route."""

import re
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from models import VChar
from server import app
from utils.validation import MAX_NAME_LENGTH, VALID_NAME_PATTERN_JS, validate_trait_names

TEST_API_KEY = "test-api-key-12345"


@pytest.fixture(autouse=True)
def mock_api_key():
    """Pin the configured API token for each test."""
    with patch.object(settings, "inconnu_api_token", TEST_API_KEY):
        yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """An HTTP client for the app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def fetch(client: AsyncClient) -> dict:
    """Fetch the constraints with a valid API key."""
    response = await client.get("/constraints", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert response.status_code == 200
    return response.json()


async def test_requires_api_key(client: AsyncClient):
    """Requests without the API key are refused."""
    response = await client.get("/constraints")
    assert response.status_code in (401, 403)


async def test_trackers_match_vchar(client: AsyncClient):
    """Tracker ranges come from VChar."""
    constraints = await fetch(client)
    assert constraints["trackers"] == {
        "health": {"min": VChar.MIN_HEALTH, "max": VChar.MAX_HEALTH},
        "willpower": {"min": VChar.MIN_WILLPOWER, "max": VChar.MAX_WILLPOWER},
    }


async def test_potency_by_splat(client: AsyncClient):
    """Only vampires and thin-bloods have Blood Potency."""
    potency = (await fetch(client))["potency"]
    assert potency == {
        "vampire": {"min": 0, "max": 10},
        "thin-blood": {"min": 0, "max": 2},
        "ghoul": None,
        "mortal": None,
    }


async def test_hunger_by_splat(client: AsyncClient):
    """Only vampires and thin-bloods have Hunger."""
    hunger = (await fetch(client))["hunger"]
    assert hunger == {
        "vampire": {"min": 0, "max": 5},
        "thin-blood": {"min": 0, "max": 5},
        "ghoul": None,
        "mortal": None,
    }


async def test_name_rules_served(client: AsyncClient):
    """Names are served in their JS form (see test_validation for why it
    matches the bot's), with the bot's length limit."""
    constraints = await fetch(client)
    assert constraints["name_pattern"] == VALID_NAME_PATTERN_JS
    assert constraints["name_max_length"] == MAX_NAME_LENGTH


@pytest.mark.parametrize(
    "name", ["Animal Ken", "Dogs'", "'Til Dawn", "Two  Spaces", "Brawl2", "a" * 41]
)
async def test_trait_rules_agree_with_bot(client: AsyncClient, name: str):
    """The served trait pattern and length accept exactly what the bot's
    format checks accept."""
    constraints = await fetch(client)
    served = (
        len(name) <= constraints["trait_max_length"]
        and re.match(constraints["trait_pattern"], name) is not None
    )
    try:
        validate_trait_names(name)
        accepted = True
    except SyntaxError, ValueError:
        accepted = False
    assert served == accepted


async def test_reserved_traits_are_name_keys(client: AsyncClient):
    """Reserved traits are served as name keys, Power Bonus included."""
    reserved = (await fetch(client))["reserved_traits"]
    assert "willpower" in reserved
    assert "current_hunger" in reserved
    assert "powerbonus" in reserved
    for key in reserved:
        with pytest.raises(ValueError):
            validate_trait_names(key)


async def test_macro_rules_served(client: AsyncClient):
    """Macro limits are served, and the name pattern needs a letter."""
    constraints = await fetch(client)
    assert constraints["macro_name_max_length"] == 50
    assert constraints["macro_comment_max_length"] == 300
    assert constraints["macro_rouses"] == {"min": 0, "max": 5}
    assert constraints["macro_difficulty"] == {"min": 0, "max": 100}
    assert constraints["macro_staining"] == ["apply", "show", "no"]
    assert constraints["macro_pool_max_tokens"] == 50
    assert constraints["pool_max"] == 100
    pattern = re.compile(constraints["macro_name_pattern"])
    assert pattern.match("_hunt_")
    assert not pattern.match("___")
    assert not pattern.match("hunt2")
