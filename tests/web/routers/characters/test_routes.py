"""Tests for character API routes."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import db as database
import discord
import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

from constants import Damage
from errors import DuplicateCharacterError
from models import VChar
from models.vchardocs import VCharProfile, VCharSplat, VCharTrait
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


@pytest.fixture
def mock_bot():
    """Mock bot with guilds list that can be configured per test."""
    bot = MagicMock(spec=discord.Bot)
    bot.guilds = []
    with patch("web.routers.characters.routes.inconnu.bot", bot):
        yield bot


@pytest.fixture
def mock_wizard_cache_pop():
    """Mock wizard_cache.pop for character creation tests."""
    with patch("web.routers.characters.routes.wizard_cache.pop") as mock:
        yield mock


@pytest.fixture
def mock_wizard_cache_get():
    """Mock wizard_cache.get for wizard endpoint tests."""
    with patch("web.routers.characters.routes.wizard_cache.get") as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_register():
    """Mock char_mgr.register for character creation tests."""
    with patch("web.routers.characters.routes.char_mgr.register", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_fetchuser():
    """Mock char_mgr.fetchuser for character list tests."""
    with patch("web.routers.characters.routes.char_mgr.fetchuser", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_fetchid():
    """Mock char_mgr.fetchid for character fetch tests."""
    with patch("web.routers.characters.routes.char_mgr.fetchid", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_guild_fetch():
    """Mock CharacterGuild.fetch for profile tests."""
    with patch("services.wizard.CharacterGuild.fetch", new_callable=AsyncMock) as mock:
        yield mock


# Factory functions for mocks


def make_mock_guild(guild_id: int, name: str, user_is_member: bool = True) -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.icon = None
    guild.get_member.return_value = MagicMock(spec=discord.Member) if user_is_member else None
    return guild


def make_mock_char(
    guild_id: int,
    user_id: int,
    name: str,
    splat: VCharSplat = VCharSplat.VAMPIRE,
    is_spc: bool = False,
) -> MagicMock:
    """Create a mock VChar."""
    char = MagicMock(spec=VChar)
    char.id = PydanticObjectId()
    char.guild = guild_id
    char.user = user_id if not is_spc else VChar.SPC_OWNER
    char.name = name
    char.splat = splat
    char.is_spc = is_spc
    return char


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


async def test_create_character_valid_api_key(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Request with valid API key proceeds."""
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        # Should not be auth error
        assert response.status_code not in [401, 403]


# Token validation tests


async def test_create_character_invalid_token(
    valid_character_data, auth_headers, mock_wizard_cache_pop
):
    """Invalid wizard token returns 404."""
    mock_wizard_cache_pop.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/characters/wizard/invalid-token",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "token" in response.json()["detail"].lower()


async def test_create_character_expired_token(
    valid_character_data, auth_headers, mock_wizard_cache_pop
):
    """Expired wizard token returns 404."""
    mock_wizard_cache_pop.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "expired" in response.json()["detail"].lower()


# Input validation tests


async def test_create_character_invalid_name(
    valid_character_data, auth_headers, mock_wizard_data, mock_wizard_cache_pop
):
    """Invalid character name returns 422."""
    valid_character_data["name"] = "A" * 31  # Too long
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_health_out_of_range(
    valid_character_data, auth_headers, mock_wizard_data, mock_wizard_cache_pop
):
    """Health out of range (4-20) returns 422."""
    valid_character_data["health"] = 3  # Too low
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_mortal_with_blood_potency(
    valid_character_data, auth_headers, mock_wizard_data, mock_wizard_cache_pop
):
    """Mortal with blood potency > 0 returns 422."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 1
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "mortal" in response.text.lower()


async def test_create_character_too_many_convictions(
    valid_character_data, auth_headers, mock_wizard_data, mock_wizard_cache_pop
):
    """More than 3 convictions returns 422."""
    valid_character_data["convictions"] = ["One", "Two", "Three", "Four"]
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_specialty_on_wrong_type(
    valid_character_data, auth_headers, mock_wizard_data, mock_wizard_cache_pop
):
    """Specialty on attribute returns 422."""
    valid_character_data["traits"][0]["subtraits"] = ["Lifting"]  # Strength is an attribute
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "cannot have subtraits" in response.text.lower()


async def test_create_duplicate_character(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Creating duplicate character (same name, guild, user) returns 422."""
    mock_wizard_cache_pop.return_value = mock_wizard_data
    mock_char_mgr_register.side_effect = DuplicateCharacterError(
        "Character 'Test Character' already exists"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "already exists" in response.text.lower()


async def test_create_duplicate_character_case_insensitive(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Duplicate check is case-insensitive."""
    valid_character_data["name"] = "TEST CHARACTER"
    mock_wizard_cache_pop.return_value = mock_wizard_data
    mock_char_mgr_register.side_effect = DuplicateCharacterError(
        "Character 'TEST CHARACTER' already exists"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "already exists" in response.text.lower()


# Character creation tests


async def test_create_vampire_success(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Valid vampire character created successfully."""
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        # Should return 201 Created
        assert response.status_code == 201
        # Should have called register
        mock_char_mgr_register.assert_called_once()
        # Should return CreationSuccess with expected fields
        result = response.json()
        assert "guild" in result
        assert "character_id" in result
        assert "character_name" in result
        assert result["character_name"] == "Test Character"


async def test_create_mortal_success(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Valid mortal character created successfully."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 0
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        mock_char_mgr_register.assert_called_once()


async def test_create_ghoul_success(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Valid ghoul character created successfully."""
    valid_character_data["splat"] = VCharSplat.GHOUL
    valid_character_data["blood_potency"] = 0
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        mock_char_mgr_register.assert_called_once()


async def test_create_thin_blood_success(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Valid thin-blood character created successfully."""
    valid_character_data["splat"] = VCharSplat.THIN_BLOOD
    valid_character_data["blood_potency"] = 2
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        mock_char_mgr_register.assert_called_once()


async def test_create_character_with_specialties(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
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
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        mock_char_mgr_register.assert_called_once()

        # Verify the specialty was properly assigned
        created_char = mock_char_mgr_register.call_args[0][0]
        academics_trait = next(t for t in created_char.raw_traits if t.name == "Academics")
        assert academics_trait.raw_subtraits == ["History", "Occult"]


async def test_token_consumed_after_creation(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Wizard token is consumed (popped) after character creation."""
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        # pop() should have been called with the token
        mock_wizard_cache_pop.assert_called_once_with(TEST_TOKEN)


async def test_character_field_mapping(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """VChar fields correctly mapped from CreationBody."""
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )

        # Get the VChar that was passed to register
        created_char = mock_char_mgr_register.call_args[0][0]
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


async def test_create_spc_character(
    valid_character_data,
    auth_headers,
    mock_spc_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """SPC character created with VChar.SPC_OWNER as user ID."""
    mock_wizard_cache_pop.return_value = mock_spc_wizard_data

    with patch("web.routers.characters.routes.VChar.SPC_OWNER", 0):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201

            # Get the VChar that was passed to register
            created_char = mock_char_mgr_register.call_args[0][0]
            assert isinstance(created_char, VChar)
            assert created_char.guild == TEST_GUILD_ID
            # SPC should have SPC_OWNER (0) as user, not the requesting user
            assert created_char.user == 0
            assert created_char.raw_name == "Test Character"


async def test_create_regular_character_user_id(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
):
    """Regular (non-SPC) character created with actual user ID."""
    mock_wizard_cache_pop.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Get the VChar that was passed to register
        created_char = mock_char_mgr_register.call_args[0][0]
        assert isinstance(created_char, VChar)
        # Regular character should have the actual user ID
        assert created_char.user == TEST_USER_ID


# Get full character tests


async def test_get_full_character_success(auth_headers, mock_char_mgr_fetchid, mock_guild_fetch):
    """Successfully fetch full character owned by user."""
    mock_char = MagicMock(spec=VChar)
    mock_char.id = PydanticObjectId()
    mock_char.guild = TEST_GUILD_ID
    mock_char.user = TEST_USER_ID
    mock_char.name = "Test Character"

    mock_guild_obj = CharacterGuild(id=TEST_GUILD_ID, name="Test Guild", icon=None)

    mock_char_mgr_fetchid.return_value = mock_char
    mock_guild_fetch.return_value = mock_guild_obj

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/{mock_char.id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "guild" in result
        assert "character" in result
        assert result["guild"]["id"] == TEST_GUILD_ID


async def test_get_full_character_not_found(auth_headers, mock_char_mgr_fetchid):
    """Character not found returns 404."""
    mock_char_mgr_fetchid.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/{PydanticObjectId()}", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


async def test_get_full_character_not_owned(auth_headers, mock_char_mgr_fetchid):
    """Accessing character not owned by user returns 403."""
    mock_char = MagicMock(spec=VChar)
    mock_char.id = PydanticObjectId()
    mock_char.user = 999999  # Different user

    mock_char_mgr_fetchid.return_value = mock_char

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/{mock_char.id}", headers=auth_headers)

        assert response.status_code == 403
        assert "does not own" in response.json()["detail"].lower()


async def test_get_full_character_missing_user_header():
    """Request missing user header returns 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/{PydanticObjectId()}",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )

        assert response.status_code == 400
        assert "user id" in response.json()["detail"].lower()


# Get wizard tests


async def test_get_wizard_success(mock_wizard_data, mock_wizard_cache_get):
    """Successfully fetch wizard with valid token."""
    mock_wizard_cache_get.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/wizard/{TEST_TOKEN}",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )

        assert response.status_code == 200
        result = response.json()
        assert "spc" in result
        assert "guild" in result
        assert "splats" in result
        assert "traits" in result
        assert result["spc"] == mock_wizard_data.spc
        assert result["guild"]["id"] == mock_wizard_data.guild.id


async def test_get_wizard_invalid_token(mock_wizard_cache_get):
    """Invalid wizard token returns 404."""
    mock_wizard_cache_get.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/characters/wizard/invalid-token",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )

        assert response.status_code == 404
        assert "token" in response.json()["detail"].lower()


async def test_get_wizard_missing_api_key():
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/wizard/{TEST_TOKEN}")
        assert response.status_code == 401


# Character list tests


async def test_get_character_list_success(auth_headers, mock_bot, mock_char_mgr_fetchuser):
    """User in multiple guilds with characters and SPCs."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    mock_bot.guilds = [guild1, guild2]

    char1 = make_mock_char(1, TEST_USER_ID, "Character 1", VCharSplat.VAMPIRE)
    char2 = make_mock_char(1, TEST_USER_ID, "Character 2", VCharSplat.MORTAL)
    char3 = make_mock_char(2, TEST_USER_ID, "Character 3", VCharSplat.GHOUL)
    spc = make_mock_char(1, TEST_USER_ID, "SPC Character", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [char1, char2, char3, spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["guilds"]) == 2
        assert len(result["characters"]) == 4
        assert result["guilds"][0]["id"] == 1
        assert result["guilds"][1]["id"] == 2


async def test_get_character_list_user_in_guilds_without_characters(
    auth_headers, mock_bot, mock_char_mgr_fetchuser
):
    """User in multiple guilds but only has characters in one."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    guild3 = make_mock_guild(3, "Guild 3")
    mock_bot.guilds = [guild1, guild2, guild3]

    char = make_mock_char(1, TEST_USER_ID, "My Character")
    spc = make_mock_char(2, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [char, spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # All 3 guilds returned even though user only has chars in 1
        assert len(result["guilds"]) == 3
        # Only characters in guilds user belongs to
        assert len(result["characters"]) == 2


async def test_get_character_list_filters_left_guilds(
    auth_headers, mock_bot, mock_char_mgr_fetchuser
):
    """Characters in guilds user has left are not returned."""
    guild1 = make_mock_guild(1, "Current Guild", user_is_member=True)
    guild2 = make_mock_guild(2, "Left Guild", user_is_member=False)
    mock_bot.guilds = [guild1, guild2]

    char_current = make_mock_char(1, TEST_USER_ID, "Current Char")
    char_left = make_mock_char(2, TEST_USER_ID, "Left Char")
    mock_char_mgr_fetchuser.return_value = [char_current, char_left]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Only guild user is in
        assert len(result["guilds"]) == 1
        assert result["guilds"][0]["id"] == 1
        # Should filter out char_left
        assert len(result["characters"]) == 1


async def test_get_character_list_no_guilds(auth_headers, mock_bot, mock_char_mgr_fetchuser):
    """User not in any guilds returns empty lists."""
    mock_bot.guilds = []
    mock_char_mgr_fetchuser.return_value = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["guilds"] == []
        assert result["characters"] == []


async def test_get_character_list_no_characters(auth_headers, mock_bot, mock_char_mgr_fetchuser):
    """User in guilds but has no characters, SPC exists."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    mock_bot.guilds = [guild1, guild2]

    spc = make_mock_char(1, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["guilds"]) == 2
        assert len(result["characters"]) == 1  # Just the SPC


async def test_get_character_list_multiple_characters_same_guild(
    auth_headers, mock_bot, mock_char_mgr_fetchuser
):
    """Multiple characters in same guild, guild not duplicated."""
    guild1 = make_mock_guild(1, "Guild 1")
    mock_bot.guilds = [guild1]

    char1 = make_mock_char(1, TEST_USER_ID, "Character 1")
    char2 = make_mock_char(1, TEST_USER_ID, "Character 2")
    char3 = make_mock_char(1, TEST_USER_ID, "Character 3")
    spc = make_mock_char(1, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [char1, char2, char3, spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["guilds"]) == 1
        assert len(result["characters"]) == 4


async def test_get_character_list_missing_api_key():
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters")
        assert response.status_code == 401


async def test_get_character_list_invalid_api_key():
    """Request with invalid API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/characters",
            headers={"Authorization": "Bearer wrong-key", "X-Discord-User-ID": str(TEST_USER_ID)},
        )
        assert response.status_code == 401


async def test_get_character_list_missing_user_header():
    """Request missing X-Discord-User-ID header returns 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/characters",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )
        assert response.status_code == 400
        assert "user id" in response.json()["detail"].lower()


# Character profile tests


async def test_get_character_profile_success(mock_guild, mock_char_mgr_fetchid, mock_guild_fetch):
    """Successfully fetch character profile."""
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

    mock_char_mgr_fetchid.return_value = mock_char
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


async def test_get_character_profile_not_found(mock_char_mgr_fetchid):
    """Character profile returns 404 when character doesn't exist."""
    mock_char_mgr_fetchid.return_value = None

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
