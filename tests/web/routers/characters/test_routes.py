"""Tests for character API routes."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

from constants import Damage
from models import VChar
from models.vchardocs import VCharSplat, VCharTrait
from server import app
from services.wizard import CharacterGuild, WizardData

# Test constants
TEST_API_KEY = "test-api-key-12345"
TEST_USER_ID = 987654321
TEST_GUILD_ID = 123456789
TEST_TOKEN = "valid-wizard-token"


@pytest.fixture(autouse=True, scope="function")
async def mock_beanie():
    """Initialize mock database for each test."""
    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    import db as database

    mock_db = client.get_database("test")
    await init_beanie(mock_db, document_models=database.models())

    # Patch the global database references to use mock database
    with patch.object(database, "characters", mock_db.characters):
        yield


@pytest.fixture(autouse=True)
def mock_api_key():
    """Mock API_KEY for all tests."""
    with patch("web.routers.characters.routes.API_KEY", TEST_API_KEY):
        yield


@pytest.fixture
def mock_guild():
    """Mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = TEST_GUILD_ID
    guild.name = "Test Guild"
    guild.icon = None
    return guild


@pytest.fixture
def mock_wizard_data(mock_guild):
    """Create mock wizard data."""
    return WizardData(
        spc=False,
        guild=CharacterGuild(id=mock_guild.id, name=mock_guild.name, icon=None),
        user=TEST_USER_ID,
    )


@pytest.fixture
def mock_spc_wizard_data(mock_guild):
    """Create mock SPC wizard data."""
    return WizardData(
        spc=True,
        guild=CharacterGuild(id=mock_guild.id, name=mock_guild.name, icon=None),
        user=TEST_USER_ID,
    )


@pytest.fixture
def valid_character_data():
    """Valid character creation data."""
    return {
        "name": "Test Character",
        "splat": VCharSplat.VAMPIRE,
        "health": 6,
        "willpower": 5,
        "humanity": 7,
        "blood_potency": 1,
        "convictions": ["Never harm innocents"],
        "biography": "A compelling backstory",
        "description": "A brief description",
        "traits": [
            {
                "name": "Strength",
                "rating": 3,
                "type": VCharTrait.Type.ATTRIBUTE,
                "subtraits": [],
            },
            {
                "name": "Athletics",
                "rating": 2,
                "type": VCharTrait.Type.SKILL,
                "subtraits": ["Running"],
            },
        ],
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "X-Discord-User-ID": str(TEST_USER_ID),
    }


# Authentication tests


async def test_create_character_missing_api_key(valid_character_data):
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
        )
        assert response.status_code == 401


async def test_create_character_invalid_api_key(valid_character_data):
    """Request with invalid API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401


async def test_create_character_valid_api_key(valid_character_data, auth_headers, mock_wizard_data):
    """Request with valid API key proceeds."""
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            # Should not be auth error
            assert response.status_code not in [401, 403]


# Token validation tests


async def test_create_character_invalid_token(valid_character_data, auth_headers):
    """Invalid wizard token returns 404."""
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/characters/wizard/invalid-token",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 404
            assert "token" in response.json()["detail"].lower()


async def test_create_character_expired_token(valid_character_data, auth_headers):
    """Expired wizard token returns 404."""
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 404
            assert "expired" in response.json()["detail"].lower()


# Input validation tests


async def test_create_character_invalid_name(valid_character_data, auth_headers, mock_wizard_data):
    """Invalid character name returns 422."""
    valid_character_data["name"] = "A" * 31  # Too long
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422


async def test_create_character_health_out_of_range(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Health out of range (4-20) returns 422."""
    valid_character_data["health"] = 3  # Too low
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422


async def test_create_character_mortal_with_blood_potency(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Mortal with blood potency > 0 returns 422."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 1
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422
            assert "mortal" in response.text.lower()


async def test_create_character_too_many_convictions(
    valid_character_data, auth_headers, mock_wizard_data
):
    """More than 3 convictions returns 422."""
    valid_character_data["convictions"] = ["One", "Two", "Three", "Four"]
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422


async def test_create_character_specialty_on_wrong_type(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Specialty on attribute returns 422."""
    valid_character_data["traits"][0]["subtraits"] = ["Lifting"]  # Strength is an attribute
    with patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422
            assert "cannot have subtraits" in response.text.lower()


async def test_create_duplicate_character(valid_character_data, auth_headers, mock_wizard_data):
    """Creating duplicate character (same name, guild, user) returns 422."""
    from errors import DuplicateCharacterError

    mock_register = AsyncMock(
        side_effect=DuplicateCharacterError("Character 'Test Character' already exists")
    )
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422
            assert "already exists" in response.text.lower()


async def test_create_duplicate_character_case_insensitive(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Duplicate check is case-insensitive."""
    from errors import DuplicateCharacterError

    # Change name to different case
    valid_character_data["name"] = "TEST CHARACTER"
    mock_register = AsyncMock(
        side_effect=DuplicateCharacterError("Character 'TEST CHARACTER' already exists")
    )
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 422
            assert "already exists" in response.text.lower()


# Character creation tests


async def test_create_vampire_success(valid_character_data, auth_headers, mock_wizard_data):
    """Valid vampire character created successfully."""
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            # Should return 201 Created
            assert response.status_code == 201
            # Should have called register
            mock_register.assert_called_once()
            # Should return CreationSuccess with expected fields
            result = response.json()
            assert "guild" in result
            assert "character_id" in result
            assert "character_name" in result
            assert result["character_name"] == "Test Character"


async def test_create_mortal_success(valid_character_data, auth_headers, mock_wizard_data):
    """Valid mortal character created successfully."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 0
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            mock_register.assert_called_once()


async def test_create_ghoul_success(valid_character_data, auth_headers, mock_wizard_data):
    """Valid ghoul character created successfully."""
    valid_character_data["splat"] = VCharSplat.GHOUL
    valid_character_data["blood_potency"] = 0
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            mock_register.assert_called_once()


async def test_create_thin_blood_success(valid_character_data, auth_headers, mock_wizard_data):
    """Valid thin-blood character created successfully."""
    valid_character_data["splat"] = VCharSplat.THIN_BLOOD
    valid_character_data["blood_potency"] = 2
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            mock_register.assert_called_once()


async def test_create_character_with_specialties(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Character with valid specialties created successfully."""
    valid_character_data["traits"].append(
        {
            "name": "Academics",
            "rating": 3,
            "type": VCharTrait.Type.SKILL,
            "subtraits": ["History", "Occult"],
        }
    )
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            mock_register.assert_called_once()

            # Verify the specialty was properly assigned
            created_char = mock_register.call_args[0][0]
            academics_trait = next(t for t in created_char.raw_traits if t.name == "Academics")
            assert academics_trait.raw_subtraits == ["History", "Occult"]


async def test_token_consumed_after_creation(valid_character_data, auth_headers, mock_wizard_data):
    """Wizard token is consumed (popped) after character creation."""
    mock_pop = MagicMock(return_value=mock_wizard_data)
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", mock_pop),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            # pop() should have been called with the token
            mock_pop.assert_called_once_with(TEST_TOKEN)


async def test_character_field_mapping(valid_character_data, auth_headers, mock_wizard_data):
    """VChar fields correctly mapped from CreationBody."""
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )

            # Get the VChar that was passed to register
            created_char = mock_register.call_args[0][0]
            assert isinstance(created_char, VChar)
            assert created_char.guild == TEST_GUILD_ID
            assert created_char.user == TEST_USER_ID
            assert created_char.raw_name == "Test Character"
            assert created_char.splat == VCharSplat.VAMPIRE
            assert created_char.raw_humanity == 7
            assert created_char.health == 6 * Damage.NONE
            assert created_char.willpower == 5 * Damage.NONE
            assert created_char.potency == 1

            # Verify post-construction assignments
            assert created_char.convictions == ["Never harm innocents"]
            assert created_char.profile.biography == "A compelling backstory"
            assert created_char.profile.description == "A brief description"

            # Verify traits were assigned and sorted
            assert len(created_char.raw_traits) == 2
            assert created_char.raw_traits[0].name == "Athletics"  # Sorted alphabetically
            assert created_char.raw_traits[0].rating == 2
            assert created_char.raw_traits[0].raw_subtraits == ["Running"]
            assert created_char.raw_traits[1].name == "Strength"
            assert created_char.raw_traits[1].rating == 3


async def test_create_spc_character(valid_character_data, auth_headers, mock_spc_wizard_data):
    """SPC character created with VChar.SPC_OWNER as user ID."""
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_spc_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
        patch("web.routers.characters.routes.VChar.SPC_OWNER", 0),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201

            # Get the VChar that was passed to register
            created_char = mock_register.call_args[0][0]
            assert isinstance(created_char, VChar)
            assert created_char.guild == TEST_GUILD_ID
            # SPC should have SPC_OWNER (0) as user, not the requesting user
            assert created_char.user == 0
            assert created_char.raw_name == "Test Character"


async def test_create_regular_character_user_id(
    valid_character_data, auth_headers, mock_wizard_data
):
    """Regular (non-SPC) character created with actual user ID."""
    mock_register = AsyncMock()
    with (
        patch("web.routers.characters.routes.wizard_cache.pop", return_value=mock_wizard_data),
        patch("web.routers.characters.routes.char_mgr.register", mock_register),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201

            # Get the VChar that was passed to register
            created_char = mock_register.call_args[0][0]
            assert isinstance(created_char, VChar)
            # Regular character should have the actual user ID
            assert created_char.user == TEST_USER_ID


# Character profile tests


async def test_get_character_profile_success(mock_guild):
    """Successfully fetch character profile."""
    from models.vchardocs import VCharProfile
    from services.wizard import CharacterGuild

    # Create a mock character with profile
    mock_char = MagicMock(spec=VChar)
    mock_char.id = PydanticObjectId()
    mock_char.guild = TEST_GUILD_ID
    mock_char.user = TEST_USER_ID
    mock_char.name = "Test Character"
    mock_char.splat = VCharSplat.VAMPIRE
    mock_char.is_spc = False
    mock_char.profile = VCharProfile()

    mock_guild_obj = CharacterGuild(id=mock_guild.id, name=mock_guild.name, icon=None)

    with (
        patch(
            "web.routers.characters.routes.char_mgr.fetchid", new_callable=AsyncMock
        ) as mock_fetchid,
        patch("services.wizard.CharacterGuild.fetch", new_callable=AsyncMock) as mock_guild_fetch,
    ):
        mock_fetchid.return_value = mock_char
        mock_guild_fetch.return_value = mock_guild_obj

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/characters/profile/{mock_char.id}",
                headers={"Authorization": f"Bearer {TEST_API_KEY}"},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["id"] == str(mock_char.id)
            assert result["spc"] is False
            assert result["guild"]["id"] == TEST_GUILD_ID
            assert result["user"] == TEST_USER_ID
            assert result["name"] == "Test Character"
            assert result["splat"] == VCharSplat.VAMPIRE
            assert "profile" in result


async def test_get_character_profile_not_found():
    """Character profile returns 404 when character doesn't exist."""
    with patch(
        "web.routers.characters.routes.char_mgr.fetchid", new_callable=AsyncMock
    ) as mock_fetchid:
        mock_fetchid.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/characters/profile/{PydanticObjectId()}",
                headers={"Authorization": f"Bearer {TEST_API_KEY}"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


async def test_get_character_profile_missing_api_key():
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/profile/{PydanticObjectId()}")
        assert response.status_code == 401


async def test_get_character_profile_invalid_api_key():
    """Request with invalid API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/profile/{PydanticObjectId()}",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401
