"""Tests for character API routes."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

import db as database
from constants import Damage
from errors import DuplicateCharacterError
from models import VChar
from models.vchardocs import VCharSplat, VCharTrait
from server import app
from services import guild_cache
from services.wizard import CharacterGuild, WizardData
from web.routers.characters.models import OwnerData

# Test constants
TEST_API_KEY = "test-api-key-12345"
TEST_USER_ID = 987654321
TEST_GUILD_ID = 123456789
TEST_TOKEN = "valid-wizard-token"
TEST_SUPPORTER_GUILD_ID = 54321
TEST_SUPPORTER_ROLE_ID = 99999


@pytest.fixture(autouse=True, scope="function")
async def mock_beanie():
    """Initialize mock database for each test."""
    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    mock_db = client.get_database("test")
    await init_beanie(mock_db, document_models=database.models())

    # Patch the global database references to use mock database
    with patch.object(database, "characters", mock_db.characters):
        yield


@pytest.fixture(autouse=True, scope="function")
async def setup_guild_cache():
    """Set up guild cache with in-memory database for each test."""
    # Patch GUILD_CACHE_LOC to use in-memory database
    with patch("config.GUILD_CACHE_LOC", "file::memory:?cache=shared"):
        # Reinitialize the guild_cache instance with new location
        guild_cache.location = "file::memory:?cache=shared"
        guild_cache._initialized = False

        await guild_cache.initialize()

        # Populate with a default guild so cache is "ready"
        # Tests that need specific guilds will call populate_guild_cache again
        default_guild = make_mock_guild(99999, "Default Guild", user_is_member=False)
        await guild_cache.upsert_guilds([default_guild])

        yield guild_cache

        if guild_cache.initialized:
            await guild_cache.close()


@pytest.fixture(autouse=True)
def mock_api_key():
    """Mock API_KEY for all tests."""
    with patch("web.routers.characters.routes.API_KEY", TEST_API_KEY):
        yield


@pytest.fixture
def mock_guild() -> discord.Guild:
    """Mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = TEST_GUILD_ID
    guild.name = "Test Guild"
    guild.icon = None
    return guild


@pytest.fixture
def mock_wizard_data(mock_guild) -> WizardData:
    """Create mock wizard data."""
    return WizardData(
        spc=False,
        guild=CharacterGuild(id=str(mock_guild.id), name=mock_guild.name, icon=None, count=None),
        user=TEST_USER_ID,
    )


@pytest.fixture
def mock_spc_wizard_data(mock_guild):
    """Create mock SPC wizard data."""
    return WizardData(
        spc=True,
        guild=CharacterGuild(id=str(mock_guild.id), name=mock_guild.name, icon=None, count=None),
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

    # Mock get_guild for guild lookup by ID
    def get_guild(guild_id: int):
        for guild in bot.guilds:
            if guild.id == guild_id:
                return guild
        return None

    bot.get_guild = MagicMock(side_effect=get_guild)

    # Mock get_or_fetch_guild for premium checks (returns None by default)
    bot.get_or_fetch_guild = AsyncMock(return_value=None)

    with patch("web.routers.characters.routes.inconnu.bot", bot):
        yield bot


@pytest.fixture
def mock_wizard_cache_pop():
    """Mock wizard_cache.get and delete for character creation tests."""
    with (
        patch("web.routers.characters.routes.wizard_cache.get") as mock_get,
        patch("web.routers.characters.routes.wizard_cache.delete") as mock_delete,
    ):
        yield mock_get, mock_delete


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


@pytest.fixture
def mock_char_mgr_fetchguild():
    """Mock char_mgr.fetchguild for guild character tests."""
    with patch("web.routers.characters.routes.char_mgr.fetchguild", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_owner_data_create():
    """Mock OwnerData.fetch for guild character tests."""
    with patch("web.routers.characters.models.OwnerData.fetch", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_countguild():
    """Mock char_mgr.countguild for character list tests."""
    with patch("web.routers.characters.routes.char_mgr.countguild", new_callable=AsyncMock) as mock:
        mock.return_value = 0
        yield mock


@pytest.fixture
def character_guild():
    """Standard CharacterGuild object for tests."""
    return CharacterGuild(id=str(TEST_GUILD_ID), name="Test Guild", icon=None, count=None)


@pytest.fixture
def owner_data():
    """Standard OwnerData object for tests."""
    return OwnerData(id=str(TEST_USER_ID), name="Test User", icon="http://avatar.png")


# Factory functions for mocks and cache helpers


async def populate_guild_cache(guilds: list[discord.Guild]) -> None:
    """Populate the guild cache with mock Discord guilds."""

    # Use refresh to clear existing guilds and replace with new ones
    await guild_cache.refresh(guilds)


def make_mock_guild(
    guild_id: int, name: str, user_is_member: bool = True, members: list | None = None
) -> MagicMock:
    """Create a mock Discord guild compatible with guild cache."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.icon = None
    guild.chunked = True  # Pretend already chunked
    guild.members = members if members is not None else []

    # Always add at least one member so cache is "ready"
    if not guild.members:
        if user_is_member:
            # Add the test user
            member = MagicMock(spec=discord.Member)
            member.id = TEST_USER_ID
            member.guild = guild
            member.name = "Test User"
            member.display_avatar.url = "http://avatar.png"
            member.guild_avatar = None
            guild.members = [member]
        else:
            # Add a different user so cache is still ready
            member = MagicMock(spec=discord.Member)
            member.id = 888888  # Different from TEST_USER_ID
            member.guild = guild
            member.name = "Other User"
            member.display_avatar.url = "http://other-avatar.png"
            member.guild_avatar = None
            guild.members = [member]

    # Mock get_member to find in members list
    def get_member(user_id: int):
        for m in guild.members:
            if m.id == user_id:
                return m
        return None

    guild.get_member = MagicMock(side_effect=get_member)

    return guild


def make_mock_char(
    guild_id: int,
    user_id: int,
    name: str,
    splat: VCharSplat = VCharSplat.VAMPIRE,
    is_spc: bool = False,
    has_left: bool = False,
) -> VChar:
    """Create a real VChar instance that can be serialized by FastAPI/Pydantic."""
    char = VChar(
        guild=guild_id,
        user=user_id if not is_spc else VChar.SPC_OWNER,
        name=name,
        splat=splat,
        humanity=7,
        health="//////",  # 6 undamaged boxes
        willpower="/////",  # 5 undamaged boxes
        potency=1,
        traits=[],
    )
    # Set ID so it appears "saved" (required by PublicCharacter.create)
    char.id = PydanticObjectId()

    # Set stat_log for "left" check
    if has_left:
        char.stat_log["left"] = True

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
    mock_bot,
):
    """Request with valid API key proceeds."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = None

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = None

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data
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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data
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
    mock_bot,
):
    """Valid vampire character created successfully."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
        assert result["has_premium"] is False


async def test_create_mortal_success(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """Valid mortal character created successfully."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 0
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_bot,
):
    """Valid ghoul character created successfully."""
    valid_character_data["splat"] = VCharSplat.GHOUL
    valid_character_data["blood_potency"] = 0
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_bot,
):
    """Valid thin-blood character created successfully."""
    valid_character_data["splat"] = VCharSplat.THIN_BLOOD
    valid_character_data["blood_potency"] = 2
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_bot,
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
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_bot,
):
    """Wizard token is consumed (popped) after character creation."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        # get() and delete() should have been called with the token
        mock_get.assert_called_once_with(TEST_TOKEN)
        mock_delete.assert_called_once_with(TEST_TOKEN)


async def test_character_field_mapping(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """VChar fields correctly mapped from CreationBody."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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
    mock_bot,
):
    """SPC character created with VChar.SPC_OWNER as user ID."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_spc_wizard_data

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
    mock_bot,
):
    """Regular (non-SPC) character created with actual user ID."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

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


# Premium status tests


async def test_create_character_premium_user(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """User with supporter role gets has_premium=True."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    # Mock supporter guild and member with role
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID

    mock_member = MagicMock(spec=discord.Member)
    mock_member.id = TEST_USER_ID
    mock_supporter_role = MagicMock(spec=discord.Role)
    mock_supporter_role.id = TEST_SUPPORTER_ROLE_ID
    mock_member.get_role = MagicMock(return_value=mock_supporter_role)

    # Mock get_or_fetch to return member
    async def mock_get_or_fetch(member_type, user_id):
        if user_id == TEST_USER_ID:
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)

    # Configure bot to return supporter guild
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch("web.routers.characters.routes.SUPPORTER_GUILD", TEST_SUPPORTER_GUILD_ID),
        patch("web.routers.characters.routes.SUPPORTER_ROLE", TEST_SUPPORTER_ROLE_ID),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            result = response.json()
            assert result["has_premium"] is True


async def test_create_character_non_premium_user(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """User in supporter guild without role gets has_premium=False."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    # Mock supporter guild and member WITHOUT role
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID

    mock_member = MagicMock(spec=discord.Member)
    mock_member.id = TEST_USER_ID
    mock_member.get_role = MagicMock(return_value=None)  # No role

    async def mock_get_or_fetch(member_type, user_id):
        if user_id == TEST_USER_ID:
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch("web.routers.characters.routes.SUPPORTER_GUILD", TEST_SUPPORTER_GUILD_ID),
        patch("web.routers.characters.routes.SUPPORTER_ROLE", TEST_SUPPORTER_ROLE_ID),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            result = response.json()
            assert result["has_premium"] is False


async def test_create_character_user_not_in_supporter_guild(
    valid_character_data,
    auth_headers,
    mock_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """User not in supporter guild gets has_premium=False."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    # Mock supporter guild but user not a member
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID
    mock_supporter_guild.get_or_fetch = AsyncMock(return_value=None)  # User not found

    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch("web.routers.characters.routes.SUPPORTER_GUILD", TEST_SUPPORTER_GUILD_ID),
        patch("web.routers.characters.routes.SUPPORTER_ROLE", TEST_SUPPORTER_ROLE_ID),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            result = response.json()
            assert result["has_premium"] is False


async def test_create_spc_premium_check_uses_wizard_creator(
    valid_character_data,
    auth_headers,
    mock_spc_wizard_data,
    mock_wizard_cache_pop,
    mock_char_mgr_register,
    mock_bot,
):
    """SPC character premium check uses wizard creator (wizard.user), not SPC_OWNER."""
    mock_get, mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_spc_wizard_data

    # Mock supporter guild
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID

    # Admin creating the SPC has premium
    mock_member = MagicMock(spec=discord.Member)
    mock_member.id = TEST_USER_ID  # wizard.user, not SPC_OWNER
    mock_supporter_role = MagicMock(spec=discord.Role)
    mock_supporter_role.id = TEST_SUPPORTER_ROLE_ID
    mock_member.get_role = MagicMock(return_value=mock_supporter_role)

    async def mock_get_or_fetch(member_type, user_id):
        if user_id == TEST_USER_ID:  # wizard.user
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch("web.routers.characters.routes.VChar.SPC_OWNER", 0),
        patch("web.routers.characters.routes.SUPPORTER_GUILD", TEST_SUPPORTER_GUILD_ID),
        patch("web.routers.characters.routes.SUPPORTER_ROLE", TEST_SUPPORTER_ROLE_ID),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/characters/wizard/{TEST_TOKEN}",
                json=valid_character_data,
                headers=auth_headers,
            )
            assert response.status_code == 201
            result = response.json()
            # SPC checks wizard creator's premium status
            assert result["has_premium"] is True


# Get full character tests


async def test_get_full_character_success(
    auth_headers,
    mock_bot,
    mock_char_mgr_fetchid,
    character_guild,
    owner_data,
):
    """Successfully fetch full character owned by user."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Test Character")

    # Mock Discord guild and member
    mock_guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=True)
    await populate_guild_cache([mock_guild])

    mock_char_mgr_fetchid.return_value = mock_char

    with patch(
        "web.routers.characters.models.OwnerData.fetch", new_callable=AsyncMock
    ) as mock_owner_create:
        mock_owner_create.return_value = owner_data

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/characters/{mock_char.id}", headers=auth_headers)

            assert response.status_code == 200
            result = response.json()

            # Verify CharData structure
            assert "guild" in result
            assert "owner" in result
            assert "character" in result
            assert "spc" in result
            assert "type" in result

            # Verify type discriminator
            assert result["type"] == "full"
            assert result["spc"] is False

            # Verify guild data
            assert result["guild"]["id"] == str(TEST_GUILD_ID)
            assert result["guild"]["name"] == "Test Guild"

            # Verify owner data
            assert result["owner"] is not None
            assert result["owner"]["id"] == str(TEST_USER_ID)
            assert result["owner"]["name"] == "Test User"

            # Verify character is VChar (full access)
            # VChar serialization includes these fields
            assert result["character"]["name"] == "Test Character"
            assert result["character"]["guild"] == TEST_GUILD_ID
            assert result["character"]["user"] == TEST_USER_ID
            assert "traits" in result["character"]  # VChar has traits


async def test_get_full_character_not_found(auth_headers, mock_char_mgr_fetchid):
    """Character not found returns 404."""
    mock_char_mgr_fetchid.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/{PydanticObjectId()}", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


async def test_get_full_character_not_owned(
    auth_headers, mock_bot, mock_char_mgr_fetchid
):
    """Non-owner accessing character receives PublicCharacter."""
    # Character owned by different user
    mock_char = make_mock_char(TEST_GUILD_ID, 999999, "Someone Else's Character")

    # Mock Discord guild and member
    mock_guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=True)
    await populate_guild_cache([mock_guild])

    mock_char_mgr_fetchid.return_value = mock_char

    # Character owner's data (NOT the requesting user)
    character_owner_data = OwnerData(
        id="999999", name="Character Owner", icon="http://owner-avatar.png"
    )

    with patch(
        "web.routers.characters.models.OwnerData.fetch", new_callable=AsyncMock
    ) as mock_owner_create:
        mock_owner_create.return_value = character_owner_data

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/characters/{mock_char.id}", headers=auth_headers)

            assert response.status_code == 200
            result = response.json()

            # Verify CharData structure
            assert "guild" in result
            assert "owner" in result
            assert "character" in result
            assert "spc" in result
            assert "type" in result

            # Verify type discriminator - should be "public" not "full"
            assert result["type"] == "public"
            assert result["spc"] is False

            # Verify guild data
            assert result["guild"]["id"] == str(TEST_GUILD_ID)

            # Verify owner data is for CHARACTER OWNER (999999), not requesting user
            assert result["owner"] is not None
            assert result["owner"]["id"] == "999999"
            assert result["owner"]["name"] == "Character Owner"
            assert result["owner"]["id"] != str(TEST_USER_ID)

            # Verify character is PublicCharacter (restricted access)
            # PublicCharacter has: id, user, name, splat, profile (no spc field)
            char_data = result["character"]
            assert char_data["id"] == str(mock_char.id)
            assert char_data["name"] == "Someone Else's Character"
            assert char_data["user"] == "999999"
            assert char_data["splat"] == VCharSplat.VAMPIRE
            assert "profile" in char_data
            # Verify PublicCharacter doesn't have sensitive fields
            assert "spc" not in char_data  # spc moved to top level


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


async def test_get_character_list_success(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """User in multiple guilds with characters and SPCs."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")

    # Populate guild cache instead of mock_bot.guilds
    await populate_guild_cache([guild1, guild2])

    char1 = make_mock_char(1, TEST_USER_ID, "Character 1", VCharSplat.VAMPIRE)
    char2 = make_mock_char(1, TEST_USER_ID, "Character 2", VCharSplat.MORTAL)
    char3 = make_mock_char(2, TEST_USER_ID, "Character 3", VCharSplat.GHOUL)
    spc = make_mock_char(1, TEST_USER_ID, "SPC Character", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [char1, char2, char3, spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()

        # Verify AuthorizedUserChars structure
        assert len(result["guilds"]) == 2
        assert len(result["characters"]) == 4
        assert result["guilds"][0]["id"] == "1"
        assert result["guilds"][1]["id"] == "2"

        # Verify characters are wrapped in CharData
        for char in result["characters"]:
            assert "guild" in char
            assert "owner" in char  # Should be None for user's own characters
            assert "character" in char
            assert "spc" in char
            assert "type" in char
            assert char["type"] == "full"
            assert char["owner"] is None  # User's own characters


async def test_get_character_list_user_in_guilds_without_characters(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """User in multiple guilds but only has characters in one."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    guild3 = make_mock_guild(3, "Guild 3")
    await populate_guild_cache([guild1, guild2, guild3])

    char = make_mock_char(1, TEST_USER_ID, "My Character")
    spc = make_mock_char(2, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [char, spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # All 3 guilds returned even though user only has chars in 2
        assert len(result["guilds"]) == 3
        # Only characters in guilds user belongs to
        assert len(result["characters"]) == 2

        # Verify wrapped structure
        for char_data in result["characters"]:
            assert char_data["type"] == "full"
            assert char_data["owner"] is None


async def test_get_character_list_filters_left_guilds(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """Characters in guilds user has left are not returned."""
    guild1 = make_mock_guild(1, "Current Guild", user_is_member=True)
    guild2 = make_mock_guild(2, "Left Guild", user_is_member=False)
    await populate_guild_cache([guild1, guild2])

    char_current = make_mock_char(1, TEST_USER_ID, "Current Char")
    char_left = make_mock_char(2, TEST_USER_ID, "Left Char")
    mock_char_mgr_fetchuser.return_value = [char_current, char_left]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Only guild user is in
        assert len(result["guilds"]) == 1
        assert result["guilds"][0]["id"] == "1"
        # Should filter out char_left
        assert len(result["characters"]) == 1
        assert result["characters"][0]["type"] == "full"


async def test_get_character_list_no_guilds(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """User not in any guilds returns empty lists."""
    # Bot is in guilds, but user is not a member of any
    other_guild = make_mock_guild(999, "Other Guild", user_is_member=False)
    await populate_guild_cache([other_guild])
    mock_char_mgr_fetchuser.return_value = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["guilds"] == []
        assert result["characters"] == []


async def test_get_character_list_no_characters(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """User in guilds but has no characters, SPC exists."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    await populate_guild_cache([guild1, guild2])

    spc = make_mock_char(1, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchuser.return_value = [spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["guilds"]) == 2
        assert len(result["characters"]) == 1  # Just the SPC
        assert result["characters"][0]["spc"] is True
        assert result["characters"][0]["type"] == "full"


async def test_get_character_list_multiple_characters_same_guild(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """Multiple characters in same guild, guild not duplicated."""
    guild1 = make_mock_guild(1, "Guild 1")
    await populate_guild_cache([guild1])

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
        # Verify all wrapped in CharData
        for char in result["characters"]:
            assert char["type"] == "full"
            assert char["guild"]["id"] == "1"


async def test_get_character_list_filters_left_characters(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """Characters marked as left are filtered out."""
    guild1 = make_mock_guild(1, "Guild 1")
    await populate_guild_cache([guild1])

    char_active = make_mock_char(1, TEST_USER_ID, "Active Character")
    char_left = make_mock_char(1, TEST_USER_ID, "Left Character", has_left=True)
    char_active2 = make_mock_char(1, TEST_USER_ID, "Another Active")
    mock_char_mgr_fetchuser.return_value = [char_active, char_left, char_active2]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["guilds"]) == 1
        # Only 2 characters returned (char_left filtered out)
        assert len(result["characters"]) == 2


async def test_get_character_list_guild_counts(
    auth_headers, mock_char_mgr_fetchuser, mock_char_mgr_countguild
):
    """Guild character counts are included in the response."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    await populate_guild_cache([guild1, guild2])

    # Return different counts per guild
    async def countguild(guild_id):
        return {1: 5, 2: 12}.get(guild_id, 0)

    mock_char_mgr_countguild.side_effect = countguild

    char1 = make_mock_char(1, TEST_USER_ID, "Character 1")
    char2 = make_mock_char(2, TEST_USER_ID, "Character 2")
    mock_char_mgr_fetchuser.return_value = [char1, char2]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()

        assert len(result["guilds"]) == 2
        guilds_by_id = {g["id"]: g for g in result["guilds"]}
        assert guilds_by_id["1"]["count"] == 5
        assert guilds_by_id["2"]["count"] == 12

        # Verify counts also appear in character guild data
        for char in result["characters"]:
            guild_id = char["guild"]["id"]
            assert char["guild"]["count"] == guilds_by_id[guild_id]["count"]


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


async def test_get_character_profile_success_non_spc(mock_char_mgr_fetchid, character_guild):
    """Successfully fetch character profile for non-SPC character."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Test Character")
    mock_char_mgr_fetchid.return_value = mock_char

    # Mock CharacterGuild.fetch and OwnerData.fetch
    owner = OwnerData(id=str(TEST_USER_ID), name="Test User", icon="http://avatar.png")

    with (
        patch(
            "web.routers.characters.routes.CharacterGuild.fetch", new_callable=AsyncMock
        ) as mock_guild_fetch,
        patch(
            "web.routers.characters.routes.OwnerData.fetch", new_callable=AsyncMock
        ) as mock_owner_create,
    ):
        mock_guild_fetch.return_value = character_guild
        mock_owner_create.return_value = owner

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/characters/profile/{mock_char.id}",
                headers={"Authorization": f"Bearer {TEST_API_KEY}"},
            )

            assert response.status_code == 200
            result = response.json()

            # Response is CharData with PublicCharacter inside
            assert "guild" in result
            assert "owner" in result
            assert "character" in result
            assert "spc" in result
            assert "type" in result

            # Verify type discriminator
            assert result["type"] == "public"
            assert result["spc"] is False

            # Verify guild data
            assert result["guild"]["id"] == str(TEST_GUILD_ID)
            assert result["guild"]["name"] == "Test Guild"

            # Verify owner data
            assert result["owner"] is not None
            assert result["owner"]["id"] == str(TEST_USER_ID)
            assert result["owner"]["name"] == "Test User"

            # Verify character is PublicCharacter (id, user, name, splat, profile)
            char_data = result["character"]
            assert char_data["id"] == str(mock_char.id)
            assert char_data["user"] == str(TEST_USER_ID)
            assert char_data["name"] == "Test Character"
            assert char_data["splat"] == VCharSplat.VAMPIRE
            assert "profile" in char_data
            # PublicCharacter doesn't have spc or guild fields
            assert "spc" not in char_data
            assert "guild" not in char_data


async def test_get_character_profile_success_spc(mock_char_mgr_fetchid, character_guild):
    """Successfully fetch character profile for SPC character."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC Character", is_spc=True)
    mock_char_mgr_fetchid.return_value = mock_char

    # Mock CharacterGuild.fetch
    with patch(
        "web.routers.characters.routes.CharacterGuild.fetch", new_callable=AsyncMock
    ) as mock_guild_fetch:
        mock_guild_fetch.return_value = character_guild

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/characters/profile/{mock_char.id}",
                headers={"Authorization": f"Bearer {TEST_API_KEY}"},
            )

            assert response.status_code == 200
            result = response.json()

            # Response is CharData with PublicCharacter inside
            assert "guild" in result
            assert "owner" in result
            assert "character" in result
            assert "spc" in result
            assert "type" in result

            # Verify type discriminator
            assert result["type"] == "public"
            assert result["spc"] is True

            # Verify guild data
            assert result["guild"]["id"] == str(TEST_GUILD_ID)

            # Verify owner is null for SPC
            assert result["owner"] is None

            # Verify character is PublicCharacter
            char_data = result["character"]
            assert char_data["id"] == str(mock_char.id)
            assert char_data["name"] == "SPC Character"
            assert char_data["splat"] == VCharSplat.VAMPIRE
            assert "profile" in char_data
            # PublicCharacter doesn't have spc or guild fields
            assert "spc" not in char_data
            assert "guild" not in char_data


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


# Guild character list tests


async def test_get_guild_characters_missing_api_key():
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}")
        assert response.status_code == 401


async def test_get_guild_characters_invalid_api_key():
    """Request with invalid API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/guild/{TEST_GUILD_ID}",
            headers={"Authorization": "Bearer wrong-key", "X-Discord-User-ID": str(TEST_USER_ID)},
        )
        assert response.status_code == 401


async def test_get_guild_characters_missing_user_header():
    """Request missing X-Discord-User-ID header returns 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/guild/{TEST_GUILD_ID}",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )
        assert response.status_code == 400
        assert "user id" in response.json()["detail"].lower()


async def test_get_guild_characters_guild_not_found(auth_headers):
    """Non-existent guild returns 404."""
    # Populate with a different guild so cache is ready
    other_guild = make_mock_guild(12345, "Other Guild", user_is_member=False)
    await populate_guild_cache([other_guild])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters/guild/999999", headers=auth_headers)
        assert response.status_code == 404
        assert "guild not found" in response.json()["detail"].lower()


async def test_get_guild_characters_user_not_member(auth_headers):
    """User not a member of guild returns 403."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=False)
    await populate_guild_cache([guild])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)
        assert response.status_code == 403
        assert "does not belong to guild" in response.json()["detail"].lower()


async def test_get_guild_characters_success(
    auth_headers, mock_char_mgr_fetchguild, mock_owner_data_create
):
    """Returns all active characters with owner data."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Character 1")
    char2 = make_mock_char(TEST_GUILD_ID, 111111, "Character 2")
    spc = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC Char", is_spc=True)
    mock_char_mgr_fetchguild.return_value = [char1, char2, spc]

    # Mock owner data creation
    owner1 = OwnerData(id=str(TEST_USER_ID), name="User1", icon="http://icon1.png")
    owner2 = OwnerData(id="111111", name="User2", icon="http://icon2.png")
    mock_owner_data_create.side_effect = [owner1, owner2]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "guild" in result
        assert "characters" in result
        assert result["guild"]["id"] == str(TEST_GUILD_ID)
        assert result["guild"]["name"] == "Test Guild"
        assert len(result["characters"]) == 3

        # Verify CharData structure
        for char in result["characters"]:
            assert "guild" in char
            assert "owner" in char
            assert "character" in char
            assert "spc" in char
            assert "type" in char
            assert char["type"] == "public"  # Guild endpoint returns PublicCharacter

        # Verify regular characters have owner data
        chars = result["characters"]
        assert chars[0]["character"]["name"] == "Character 1"
        assert chars[0]["owner"]["name"] == "User1"
        assert chars[0]["spc"] is False
        assert chars[1]["character"]["name"] == "Character 2"
        assert chars[1]["owner"]["name"] == "User2"
        assert chars[1]["spc"] is False

        # Verify SPC has null owner
        assert chars[2]["character"]["name"] == "SPC Char"
        assert chars[2]["spc"] is True
        assert chars[2]["owner"] is None


async def test_get_guild_characters_empty_guild(auth_headers, mock_char_mgr_fetchguild):
    """Empty guild returns empty list."""
    guild = make_mock_guild(TEST_GUILD_ID, "Empty Guild")
    await populate_guild_cache([guild])
    mock_char_mgr_fetchguild.return_value = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "guild" in result
        assert "characters" in result
        assert result["guild"]["id"] == str(TEST_GUILD_ID)
        assert result["guild"]["name"] == "Empty Guild"
        assert result["characters"] == []


async def test_get_guild_characters_multiple_owners(
    auth_headers, mock_char_mgr_fetchguild, mock_owner_data_create
):
    """Guild with characters from different users."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, 100, "User1 Char")
    char2 = make_mock_char(TEST_GUILD_ID, 200, "User2 Char")
    char3 = make_mock_char(TEST_GUILD_ID, 300, "User3 Char")
    mock_char_mgr_fetchguild.return_value = [char1, char2, char3]

    owner1 = OwnerData(id="100", name="User1", icon="http://icon1.png")
    owner2 = OwnerData(id="200", name="User2", icon="http://icon2.png")
    owner3 = OwnerData(id="300", name="User3", icon="http://icon3.png")
    mock_owner_data_create.side_effect = [owner1, owner2, owner3]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "guild" in result
        assert "characters" in result
        chars = result["characters"]
        assert len(chars) == 3
        assert chars[0]["character"]["name"] == "User1 Char"
        assert chars[0]["owner"]["name"] == "User1"
        assert chars[1]["character"]["name"] == "User2 Char"
        assert chars[1]["owner"]["name"] == "User2"
        assert chars[2]["character"]["name"] == "User3 Char"
        assert chars[2]["owner"]["name"] == "User3"


async def test_get_guild_characters_filters_left(
    auth_headers, mock_char_mgr_fetchguild, mock_owner_data_create
):
    """Characters marked as left are excluded."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char_active = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Active Char")
    char_left = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Left Char", has_left=True)
    char_active2 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Another Active")
    mock_char_mgr_fetchguild.return_value = [char_active, char_left, char_active2]

    owner = OwnerData(id=str(TEST_USER_ID), name="User", icon="http://icon.png")
    mock_owner_data_create.side_effect = [owner, owner]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Only 2 active characters returned
        chars = result["characters"]
        assert len(chars) == 2
        assert chars[0]["character"]["name"] == "Active Char"
        assert chars[1]["character"]["name"] == "Another Active"


async def test_get_guild_characters_filters_missing_owners(
    auth_headers, mock_char_mgr_fetchguild, mock_owner_data_create
):
    """Characters whose owners can't be found are excluded."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, 100, "Valid Owner")
    char2 = make_mock_char(TEST_GUILD_ID, 200, "Missing Owner")
    char3 = make_mock_char(TEST_GUILD_ID, 300, "Another Valid")
    mock_char_mgr_fetchguild.return_value = [char1, char2, char3]

    owner1 = OwnerData(id="100", name="User1", icon="http://icon1.png")
    owner3 = OwnerData(id="300", name="User3", icon="http://icon3.png")
    # char2's owner returns None (can't be found)
    mock_owner_data_create.side_effect = [owner1, None, owner3]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Only 2 characters with valid owners returned
        chars = result["characters"]
        assert len(chars) == 2
        assert chars[0]["character"]["name"] == "Valid Owner"
        assert chars[1]["character"]["name"] == "Another Valid"


async def test_get_guild_characters_mixed_filtering(
    auth_headers, mock_char_mgr_fetchguild, mock_owner_data_create
):
    """Guild with active chars, left chars, and chars with missing owners."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char_active = make_mock_char(TEST_GUILD_ID, 100, "Active Char")
    char_left = make_mock_char(TEST_GUILD_ID, 200, "Left Char", has_left=True)
    char_missing_owner = make_mock_char(TEST_GUILD_ID, 300, "Missing Owner")
    char_active2 = make_mock_char(TEST_GUILD_ID, 400, "Another Active")
    spc = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC", is_spc=True)
    mock_char_mgr_fetchguild.return_value = [
        char_active,
        char_left,
        char_missing_owner,
        char_active2,
        spc,
    ]

    owner1 = OwnerData(id="100", name="User1", icon="http://icon1.png")
    owner4 = OwnerData(id="400", name="User4", icon="http://icon4.png")
    # char_left is filtered before owner creation
    # char_missing_owner's owner returns None
    mock_owner_data_create.side_effect = [owner1, None, owner4]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Only active chars with valid owners + SPC
        chars = result["characters"]
        assert len(chars) == 3
        assert chars[0]["character"]["name"] == "Active Char"
        assert chars[0]["spc"] is False
        assert chars[1]["character"]["name"] == "Another Active"
        assert chars[1]["spc"] is False
        assert chars[2]["character"]["name"] == "SPC"
        assert chars[2]["spc"] is True  # spc at top level, not in character


async def test_get_guild_characters_spc_owner_data_null(
    auth_headers, mock_char_mgr_fetchguild
):
    """SPCs have owner as null."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    spc = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Test SPC", is_spc=True)
    mock_char_mgr_fetchguild.return_value = [spc]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        chars = result["characters"]
        assert len(chars) == 1
        assert chars[0]["spc"] is True  # spc at top level in CharData
        assert chars[0]["type"] == "public"
        assert chars[0]["owner"] is None
        # PublicCharacter doesn't have spc field
        assert "spc" not in chars[0]["character"]


async def test_get_guild_characters_only_spcs(auth_headers, mock_char_mgr_fetchguild):
    """Guild with only SPCs returns all SPCs with null owner."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    spc1 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC 1", is_spc=True)
    spc2 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC 2", is_spc=True)
    spc3 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC 3", is_spc=True)
    mock_char_mgr_fetchguild.return_value = [spc1, spc2, spc3]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        chars = result["characters"]
        assert len(chars) == 3
        for char in chars:
            assert char["spc"] is True  # spc at top level in CharData
            assert char["type"] == "public"
            assert char["owner"] is None
            assert "spc" not in char["character"]  # PublicCharacter doesn't have spc
