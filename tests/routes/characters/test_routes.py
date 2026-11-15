"""Tests for character API routes."""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

import db as database
import routes.characters.routes as routes_module
from config import settings
from constants import Damage
from errors import DuplicateCharacterError
from events import CharEvents, CharEventType, char_events
from models import VChar
from models.vchardocs import VCharSplat, VCharTrait
from routes.characters.models import OwnerData, with_core_traits
from routes.characters.routes import char_event_stream
from routes.deps import get_bot
from server import app
from services import char_mgr, guild_cache
from services.guildcache import GuildCache
from services.wizard import CharacterGuild, WizardData

# Test constants
TEST_API_KEY = "test-api-key-12345"
TEST_USER_ID = 987654321
TEST_GUILD_ID = 123456789
TEST_TOKEN = "valid-wizard-token"
TEST_SUPPORTER_GUILD_ID = 54321
TEST_SUPPORTER_ROLE_ID = 99999

type MockAsyncFn = AsyncMock
type MockBot = MagicMock
type MockChannel = AsyncMock
type MockFn = MagicMock
type MockGuild = MagicMock
type MockMember = MagicMock


@pytest.fixture(autouse=True, scope="function")
async def mock_beanie() -> AsyncIterator[None]:
    """Initialize mock database for each test."""
    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    mock_db = client.get_database("test")
    await init_beanie(mock_db, document_models=database.models())

    # Patch the global database references to use mock database
    with patch.object(database, "characters", mock_db.characters):
        yield


@pytest.fixture(autouse=True, scope="function")
async def setup_guild_cache() -> AsyncIterator[GuildCache]:
    """Set up guild cache with in-memory database for each test."""
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
def mock_api_key() -> Iterator[None]:
    """Mock API_KEY for all tests."""
    with patch.object(settings, "inconnu_api_token", TEST_API_KEY):
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
def mock_wizard_data(mock_guild: discord.Guild) -> WizardData:
    """Create mock wizard data."""
    return WizardData(
        spc=False,
        guild=CharacterGuild(id=str(mock_guild.id), name=mock_guild.name, icon=None, count=None),
        user=TEST_USER_ID,
    )


@pytest.fixture
def mock_spc_wizard_data(mock_guild: discord.Guild) -> WizardData:
    """Create mock SPC wizard data."""
    return WizardData(
        spc=True,
        guild=CharacterGuild(id=str(mock_guild.id), name=mock_guild.name, icon=None, count=None),
        user=TEST_USER_ID,
    )


@pytest.fixture
def valid_character_data() -> dict[str, Any]:
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
def auth_headers() -> dict[str, str]:
    """Authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "X-Discord-User-ID": str(TEST_USER_ID),
    }


@pytest.fixture
def mock_bot() -> Iterator[MockBot]:
    """Mock bot with guilds list that can be configured per test."""
    bot = MagicMock(spec=discord.Bot)
    bot.guilds = []

    # Mock get_guild for guild lookup by ID
    def get_guild(guild_id: int) -> discord.Guild | None:
        """Find a guild in bot.guilds."""
        for guild in bot.guilds:
            if guild.id == guild_id:
                return guild
        return None

    bot.get_guild = MagicMock(side_effect=get_guild)

    # Mock get_or_fetch_guild for premium checks (returns None by default)
    bot.get_or_fetch_guild = AsyncMock(return_value=None)

    with patch.dict(app.dependency_overrides, {get_bot: lambda: bot}):
        yield bot


@pytest.fixture
def mock_wizard_cache_pop() -> Iterator[tuple[MockFn, MockFn]]:
    """Mock wizard_cache.get and delete for character creation tests."""
    with (
        patch("routes.characters.routes.wizard_cache.get") as mock_get,
        patch("routes.characters.routes.wizard_cache.delete") as mock_delete,
    ):
        yield mock_get, mock_delete


@pytest.fixture
def mock_wizard_cache_get() -> Iterator[MockFn]:
    """Mock wizard_cache.get for wizard endpoint tests."""
    with patch("routes.characters.routes.wizard_cache.get") as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_register() -> Iterator[MockAsyncFn]:
    """Mock char_mgr.register for character creation tests."""
    with patch("routes.characters.routes.char_mgr.register", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_fetchuser() -> Iterator[MockAsyncFn]:
    """Mock char_mgr.fetchuser for character list tests."""
    with patch("routes.characters.routes.char_mgr.fetchuser", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_fetchid() -> Iterator[MockAsyncFn]:
    """Mock char_mgr.fetchid for character fetch tests."""
    with patch("routes.characters.routes.char_mgr.fetchid", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_guild_fetch() -> Iterator[MockAsyncFn]:
    """Mock CharacterGuild.fetch for profile tests."""
    with patch("services.wizard.CharacterGuild.fetch", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_fetchguild() -> Iterator[MockAsyncFn]:
    """Mock char_mgr.fetchguild for guild character tests."""
    with patch("routes.characters.routes.char_mgr.fetchguild", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_char_mgr_countguild() -> Iterator[MockAsyncFn]:
    """Mock char_mgr.countguild for character list tests."""
    with patch("routes.characters.routes.char_mgr.countguild", new_callable=AsyncMock) as mock:
        mock.return_value = 0
        yield mock


@pytest.fixture
def character_guild() -> CharacterGuild:
    """Standard CharacterGuild object for tests."""
    return CharacterGuild(id=str(TEST_GUILD_ID), name="Test Guild", icon=None, count=None)


@pytest.fixture
def owner_data() -> OwnerData:
    """Standard OwnerData object for tests."""
    return OwnerData(id=str(TEST_USER_ID), name="Test User", icon="http://avatar.png")


# Factory functions for mocks and cache helpers


async def populate_guild_cache(guilds: list[discord.Guild]) -> None:
    """Populate the guild cache with mock Discord guilds."""

    # Use refresh to clear existing guilds and replace with new ones
    await guild_cache.refresh(guilds)


def make_mock_guild(
    guild_id: int,
    name: str,
    user_is_member: bool = True,
    members: list[discord.Member] | None = None,
) -> MockGuild:
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
            member.display_name = "Test User"
            member.display_avatar.url = "http://avatar.png"
            member.guild_avatar = None
            guild.members = [member]
        else:
            # Add a different user so cache is still ready
            member = MagicMock(spec=discord.Member)
            member.id = 888888  # Different from TEST_USER_ID
            member.guild = guild
            member.display_name = "Other User"
            member.display_avatar.url = "http://other-avatar.png"
            member.guild_avatar = None
            guild.members = [member]

    # Mock get_member to find in members list
    def get_member(user_id: int) -> discord.Member | None:
        """Find a member in the guild."""
        for m in guild.members:
            if m.id == user_id:
                return m
        return None

    guild.get_member = MagicMock(side_effect=get_member)

    return guild


def make_mock_member(guild: MockGuild, user_id: int, name: str) -> MockMember:
    """Create a mock Discord member and add it to the guild."""
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.guild = guild
    member.display_name = name
    member.display_avatar.url = f"http://icon{user_id}.png"
    member.guild_avatar = None
    guild.members.append(member)
    return member


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

    # Set log for "left" check
    if has_left:
        char.log.left = discord.utils.utcnow()

    return char


# Authentication tests


async def test_create_character_missing_api_key(valid_character_data: dict[str, Any]):
    """Request without API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
        )
        assert response.status_code == 401


async def test_create_character_invalid_api_key(valid_character_data: dict[str, Any]):
    """Request with invalid API key rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401


async def test_create_character_valid_api_key(
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Request with valid API key proceeds."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Invalid wizard token returns 404."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Expired wizard token returns 404."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Invalid character name returns 422."""
    valid_character_data["name"] = "A" * 31  # Too long
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_health_out_of_range(
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Health out of range (4-20) returns 422."""
    valid_character_data["health"] = 3  # Too low
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_mortal_with_blood_potency(
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Mortal with blood potency > 0 returns 422."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 1
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """More than 3 convictions returns 422."""
    valid_character_data["convictions"] = ["One", "Two", "Three", "Four"]
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/characters/wizard/{TEST_TOKEN}",
            json=valid_character_data,
            headers=auth_headers,
        )
        assert response.status_code == 422


async def test_create_character_specialty_on_wrong_type(
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
):
    """Specialty on attribute returns 422."""
    valid_character_data["traits"][0]["subtraits"] = ["Lifting"]  # Strength is an attribute
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
):
    """Creating duplicate character (same name, guild, user) returns 422."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
):
    """Duplicate check is case-insensitive."""
    valid_character_data["name"] = "TEST CHARACTER"
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Valid vampire character created successfully."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Valid mortal character created successfully."""
    valid_character_data["splat"] = VCharSplat.MORTAL
    valid_character_data["blood_potency"] = 0
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Valid ghoul character created successfully."""
    valid_character_data["splat"] = VCharSplat.GHOUL
    valid_character_data["blood_potency"] = 0
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Valid thin-blood character created successfully."""
    valid_character_data["splat"] = VCharSplat.THIN_BLOOD
    valid_character_data["blood_potency"] = 2
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
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
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """VChar fields correctly mapped from CreationBody."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_spc_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """SPC character created with VChar.SPC_OWNER as user ID."""
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_spc_wizard_data

    with patch("routes.characters.routes.VChar.SPC_OWNER", 0):
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """Regular (non-SPC) character created with actual user ID."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """User with supporter role gets has_premium=True."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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
    async def mock_get_or_fetch(
        member_type: type[discord.Member], user_id: int
    ) -> discord.Member | None:
        """Return the test member, if it's the one sought."""
        if user_id == TEST_USER_ID:
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)

    # Configure bot to return supporter guild
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch.object(settings, "supporter_guild", TEST_SUPPORTER_GUILD_ID),
        patch.object(settings, "supporter_role", TEST_SUPPORTER_ROLE_ID),
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """User in supporter guild without role gets has_premium=False."""
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    # Mock supporter guild and member WITHOUT role
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID

    mock_member = MagicMock(spec=discord.Member)
    mock_member.id = TEST_USER_ID
    mock_member.get_role = MagicMock(return_value=None)  # No role

    async def mock_get_or_fetch(
        member_type: type[discord.Member], user_id: int
    ) -> discord.Member | None:
        """Return the test member, if it's the one sought."""
        if user_id == TEST_USER_ID:
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch.object(settings, "supporter_guild", TEST_SUPPORTER_GUILD_ID),
        patch.object(settings, "supporter_role", TEST_SUPPORTER_ROLE_ID),
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """User not in supporter guild gets has_premium=False."""
    mock_get, _mock_delete = mock_wizard_cache_pop
    mock_get.return_value = mock_wizard_data

    # Mock supporter guild but user not a member
    mock_supporter_guild = MagicMock(spec=discord.Guild)
    mock_supporter_guild.id = TEST_SUPPORTER_GUILD_ID
    mock_supporter_guild.get_or_fetch = AsyncMock(return_value=None)  # User not found

    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch.object(settings, "supporter_guild", TEST_SUPPORTER_GUILD_ID),
        patch.object(settings, "supporter_role", TEST_SUPPORTER_ROLE_ID),
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
    valid_character_data: dict[str, Any],
    auth_headers: dict[str, str],
    mock_spc_wizard_data: WizardData,
    mock_wizard_cache_pop: tuple[MockFn, MockFn],
    mock_char_mgr_register: MockAsyncFn,
    mock_bot: MockBot,
):
    """SPC character premium check uses wizard creator (wizard.user), not SPC_OWNER."""
    mock_get, _mock_delete = mock_wizard_cache_pop
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

    async def mock_get_or_fetch(
        member_type: type[discord.Member], user_id: int
    ) -> discord.Member | None:
        """Return the test member, if it's the one sought."""
        if user_id == TEST_USER_ID:  # wizard.user
            return mock_member
        return None

    mock_supporter_guild.get_or_fetch = AsyncMock(side_effect=mock_get_or_fetch)
    mock_bot.get_or_fetch_guild = AsyncMock(return_value=mock_supporter_guild)

    with (
        patch("routes.characters.routes.VChar.SPC_OWNER", 0),
        patch.object(settings, "supporter_guild", TEST_SUPPORTER_GUILD_ID),
        patch.object(settings, "supporter_role", TEST_SUPPORTER_ROLE_ID),
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
    auth_headers: dict[str, str],
    mock_bot: MockBot,
    mock_char_mgr_fetchid: MockAsyncFn,
    character_guild: CharacterGuild,
    owner_data: OwnerData,
):
    """Successfully fetch full character owned by user."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Test Character")

    # Mock Discord guild and member
    mock_guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=True)
    await populate_guild_cache([mock_guild])

    mock_char_mgr_fetchid.return_value = mock_char

    with patch(
        "routes.characters.models.OwnerData.fetch", new_callable=AsyncMock
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


async def test_get_full_character_not_found(
    auth_headers: dict[str, str], mock_char_mgr_fetchid: MockAsyncFn
):
    """Character not found returns 404."""
    mock_char_mgr_fetchid.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/{PydanticObjectId()}", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


async def test_get_full_character_not_owned(
    auth_headers: dict[str, str], mock_bot: MockBot, mock_char_mgr_fetchid: MockAsyncFn
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
        "routes.characters.models.OwnerData.fetch", new_callable=AsyncMock
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


@pytest.mark.parametrize("storyteller,expected_type", [(True, "full"), (False, "public")])
async def test_get_full_character_storyteller(
    auth_headers: dict[str, str],
    mock_bot: MockBot,
    mock_char_mgr_fetchid: MockAsyncFn,
    storyteller: bool,
    expected_type: str,
):
    """Storytellers get other players' full characters, and others get the
    public view. The check runs on the requester's cached Discord member."""
    mock_char = make_mock_char(TEST_GUILD_ID, 999999, "Someone Else's Character")
    mock_guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=True)
    await populate_guild_cache([mock_guild])
    mock_bot.guilds = [mock_guild]
    mock_char_mgr_fetchid.return_value = mock_char
    owner = OwnerData(id="999999", name="Character Owner", icon="http://owner-avatar.png")

    with (
        patch(
            "routes.characters.models.OwnerData.fetch", new_callable=AsyncMock, return_value=owner
        ),
        patch(
            "routes.characters.routes.is_storyteller",
            new_callable=AsyncMock,
            return_value=storyteller,
        ) as mock_is_storyteller,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/characters/{mock_char.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["type"] == expected_type
    mock_is_storyteller.assert_awaited_once_with(mock_guild.get_member(TEST_USER_ID))


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


async def test_get_wizard_success(mock_wizard_data: WizardData, mock_wizard_cache_get: MockFn):
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


async def test_get_wizard_invalid_token(mock_wizard_cache_get: MockFn):
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchuser: MockAsyncFn,
    mock_char_mgr_countguild: MockAsyncFn,
):
    """Guild character counts are included in the response."""
    guild1 = make_mock_guild(1, "Guild 1")
    guild2 = make_mock_guild(2, "Guild 2")
    await populate_guild_cache([guild1, guild2])

    # Return different counts per guild
    async def countguild(guild_id: int) -> int:
        """Return each guild's character count."""
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


async def test_get_character_profile_success_non_spc(
    mock_char_mgr_fetchid: MockAsyncFn, character_guild: CharacterGuild
):
    """Successfully fetch character profile for non-SPC character."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Test Character")
    mock_char_mgr_fetchid.return_value = mock_char

    # Mock CharacterGuild.fetch and OwnerData.fetch
    owner = OwnerData(id=str(TEST_USER_ID), name="Test User", icon="http://avatar.png")

    with (
        patch(
            "routes.characters.routes.CharacterGuild.fetch", new_callable=AsyncMock
        ) as mock_guild_fetch,
        patch(
            "routes.characters.routes.OwnerData.fetch", new_callable=AsyncMock
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


async def test_get_character_profile_success_spc(
    mock_char_mgr_fetchid: MockAsyncFn, character_guild: CharacterGuild
):
    """Successfully fetch character profile for SPC character."""
    mock_char = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC Character", is_spc=True)
    mock_char_mgr_fetchid.return_value = mock_char

    # Mock CharacterGuild.fetch
    with patch(
        "routes.characters.routes.CharacterGuild.fetch", new_callable=AsyncMock
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


async def test_get_character_profile_not_found(mock_char_mgr_fetchid: MockAsyncFn):
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


async def test_get_guild_characters_guild_not_found(auth_headers: dict[str, str]):
    """Non-existent guild returns 404."""
    # Populate with a different guild so cache is ready
    other_guild = make_mock_guild(12345, "Other Guild", user_is_member=False)
    await populate_guild_cache([other_guild])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/characters/guild/999999", headers=auth_headers)
        assert response.status_code == 404
        assert "guild not found" in response.json()["detail"].lower()


async def test_get_guild_characters_user_not_member(auth_headers: dict[str, str]):
    """User not a member of guild returns 403."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=False)
    await populate_guild_cache([guild])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/characters/guild/{TEST_GUILD_ID}", headers=auth_headers)
        assert response.status_code == 403
        assert "does not belong to guild" in response.json()["detail"].lower()


async def test_get_guild_characters_success(
    auth_headers: dict[str, str],
    mock_char_mgr_fetchguild: MockAsyncFn,
):
    """Returns all active characters with owner data."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    make_mock_member(guild, 111111, "User2")
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Character 1")
    char2 = make_mock_char(TEST_GUILD_ID, 111111, "Character 2")
    spc = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "SPC Char", is_spc=True)
    mock_char_mgr_fetchguild.return_value = [char1, char2, spc]

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
        assert chars[0]["owner"]["name"] == "Test User"
        assert chars[0]["spc"] is False
        assert chars[1]["character"]["name"] == "Character 2"
        assert chars[1]["owner"] == {
            "id": "111111",
            "name": "User2",
            "icon": "http://icon111111.png",
        }
        assert chars[1]["spc"] is False

        # Verify SPC has null owner
        assert chars[2]["character"]["name"] == "SPC Char"
        assert chars[2]["spc"] is True
        assert chars[2]["owner"] is None


async def test_get_guild_characters_empty_guild(
    auth_headers: dict[str, str], mock_char_mgr_fetchguild: MockAsyncFn
):
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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchguild: MockAsyncFn,
):
    """Guild with characters from different users."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    for user_id in (100, 200, 300):
        make_mock_member(guild, user_id, f"User{user_id // 100}")
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, 100, "User1 Char")
    char2 = make_mock_char(TEST_GUILD_ID, 200, "User2 Char")
    char3 = make_mock_char(TEST_GUILD_ID, 300, "User3 Char")
    mock_char_mgr_fetchguild.return_value = [char1, char2, char3]

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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchguild: MockAsyncFn,
):
    """Characters marked as left are excluded."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    await populate_guild_cache([guild])

    char_active = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Active Char")
    char_left = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Left Char", has_left=True)
    char_active2 = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Another Active")
    mock_char_mgr_fetchguild.return_value = [char_active, char_left, char_active2]

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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchguild: MockAsyncFn,
):
    """Characters whose owners can't be found are excluded."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    make_mock_member(guild, 100, "User1")
    make_mock_member(guild, 300, "User3")  # 200 isn't cached
    await populate_guild_cache([guild])

    char1 = make_mock_char(TEST_GUILD_ID, 100, "Valid Owner")
    char2 = make_mock_char(TEST_GUILD_ID, 200, "Missing Owner")
    char3 = make_mock_char(TEST_GUILD_ID, 300, "Another Valid")
    mock_char_mgr_fetchguild.return_value = [char1, char2, char3]

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
    auth_headers: dict[str, str],
    mock_char_mgr_fetchguild: MockAsyncFn,
):
    """Guild with active chars, left chars, and chars with missing owners."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild")
    for user_id in (100, 200, 400):  # 300 isn't cached
        make_mock_member(guild, user_id, f"User{user_id // 100}")
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
    auth_headers: dict[str, str], mock_char_mgr_fetchguild: MockAsyncFn
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


async def test_get_guild_characters_only_spcs(
    auth_headers: dict[str, str], mock_char_mgr_fetchguild: MockAsyncFn
):
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


# Character events


async def test_character_events_not_found(
    auth_headers: dict[str, str], mock_char_mgr_fetchid: MockAsyncFn
):
    """Streaming a missing character returns 404."""
    mock_char_mgr_fetchid.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/{PydanticObjectId()}/events", headers=auth_headers
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Character not found"


async def test_character_events_guild_not_found(
    auth_headers: dict[str, str], mock_char_mgr_fetchid: MockAsyncFn
):
    """Streaming a character whose guild isn't cached returns 404."""
    mock_char_mgr_fetchid.return_value = make_mock_char(TEST_GUILD_ID, TEST_USER_ID, "Char")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/{PydanticObjectId()}/events", headers=auth_headers
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Guild not found"


async def test_character_events_not_member(
    auth_headers: dict[str, str], mock_char_mgr_fetchid: MockAsyncFn
):
    """Only members of the character's guild may stream its events."""
    await populate_guild_cache([make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=False)])
    mock_char_mgr_fetchid.return_value = make_mock_char(TEST_GUILD_ID, 999999, "Char")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/characters/{PydanticObjectId()}/events", headers=auth_headers
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not in character's guild"


async def test_character_events_starting_up(auth_headers: dict[str, str]):
    """Streaming before the guild cache is ready returns 503."""
    with patch.object(guild_cache, "ready", new_callable=AsyncMock, return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/characters/{PydanticObjectId()}/events", headers=auth_headers
            )

    assert response.status_code == 503


async def test_character_events_member_streams(
    auth_headers: dict[str, str], mock_char_mgr_fetchid: MockAsyncFn
):
    """A guild member gets an event stream, even for someone else's character."""
    await populate_guild_cache([make_mock_guild(TEST_GUILD_ID, "Test Guild")])
    char = make_mock_char(TEST_GUILD_ID, 999999, "Char")
    mock_char_mgr_fetchid.return_value = char

    with patch.object(
        routes_module, "char_event_stream", autospec=True, return_value=empty_stream()
    ) as stream:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/characters/{char.id}/events", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    stream.assert_called_once_with(char.id_str)


async def empty_stream() -> AsyncGenerator[str]:
    """An event stream that ends at once, so the client can finish reading."""
    yield "retry: 5000\n\n"


@pytest.fixture
def oid() -> str:
    """A character ID of the test's own, so a stream a failed test leaves open
    can't affect the others."""
    return str(PydanticObjectId())


async def test_event_stream_relays_events(oid: str):
    """The stream sets the retry delay, then relays each event."""
    stream = char_event_stream(oid)
    assert await anext(stream) == "retry: 5000\n\n"

    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    char_events.publish(oid)
    assert await pending == "data: changed\n\n"
    await stream.aclose()


async def test_event_stream_ends_on_deletion(oid: str):
    """The stream ends after a deletion and unsubscribes."""
    stream = char_event_stream(oid)
    await anext(stream)

    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    char_events.publish(oid, CharEventType.DELETED)
    assert await pending == "data: deleted\n\n"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert char_events.subscribers(oid) == 0


async def test_event_stream_pings_when_quiet(oid: str):
    """The stream pings when nothing happens, so dead connections surface."""
    stream = char_event_stream(oid, heartbeat=0.01)
    await anext(stream)
    assert await anext(stream) == ": ping\n\n"
    await stream.aclose()
    assert char_events.subscribers(oid) == 0


async def test_event_stream_ends_quietly_on_close(oid: str):
    """Shutdown ends the stream without sending anything; the client
    reconnects on its own."""
    events = CharEvents()  # Closing the shared one would end other tests' streams
    with patch.object(routes_module, "char_events", events):
        stream = char_event_stream(oid)
        await anext(stream)
        events.close()
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
    assert events.subscribers(oid) == 0


# Character edits


EDIT_OWNER_TRAITS = [
    VCharTrait(name="Strength", rating=3, type=VCharTrait.Type.ATTRIBUTE, subtraits=["Lifting"]),
    VCharTrait(name="Athletics", rating=2, type=VCharTrait.Type.SKILL, subtraits=["Running"]),
    VCharTrait(name="Potence", rating=2, type=VCharTrait.Type.DISCIPLINE, subtraits=["Prowess"]),
    VCharTrait(name="Cooking", rating=1, type=VCharTrait.Type.CUSTOM),
]


async def make_saved_char(
    splat=VCharSplat.VAMPIRE,
    user_id=TEST_USER_ID,
    potency=1,
    convictions: list[str] | None = None,
) -> VChar:
    """Insert a character with a full set of core traits, as the wizard makes."""
    char = VChar(
        guild=TEST_GUILD_ID,
        user=user_id,
        name="Nadea Theron",
        splat=splat,
        humanity=7,
        stains=0,
        health="......",
        willpower=".....",
        potency=potency,
        convictions=convictions or [],
        traits=with_core_traits([t.model_copy(deep=True) for t in EDIT_OWNER_TRAITS]),
    )
    await char.insert()
    return char


def edit_body(char: VChar, **overrides: Any) -> dict[str, Any]:
    """A PATCH body that leaves the character as it is, plus overrides."""
    body: dict[str, Any] = {
        "name": char.raw_name,
        "health": char.health,
        "willpower": char.willpower,
        "humanity": char.raw_humanity,
        "stains": char.stains,
        "convictions": char.convictions,
        "profile": {
            "description": char.profile.description,
            "biography": char.profile.biography,
        },
        "traits": [t.model_dump(by_alias=True) for t in char.raw_traits],
    }
    if char.is_vampire:
        body["potency"] = char.potency
        body["hunger"] = char.raw_hunger
    body.update(overrides)
    return body


def body_traits(char: VChar, *, drop=(), add=(), **changes: dict[str, Any]) -> list[dict[str, Any]]:
    """The character's traits as a body list, minus drop, plus add, with
    per-trait field changes (by name)."""
    traits = []
    for trait in char.raw_traits:
        if trait.name in drop:
            continue
        data = trait.model_dump(by_alias=True)
        data.update(changes.get(trait.name, {}))
        traits.append(data)
    return traits + list(add)


@pytest.fixture
async def edit_guild(mock_bot: MockBot) -> MockGuild:
    """The character's guild, with the test user as a member."""
    guild = make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=True)
    await populate_guild_cache([guild])
    mock_bot.guilds = [guild]
    return guild


@pytest.fixture
def update_channel() -> Iterator[MockChannel]:
    """The guild's update channel."""
    channel = AsyncMock(spec=discord.TextChannel)
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        yield channel


@pytest.fixture
def no_duplicates() -> Iterator[MockAsyncFn]:
    """No other character has the requested name."""
    with patch.object(char_mgr, "has_character", new_callable=AsyncMock, return_value=False) as m:
        yield m


async def patch_char(char: VChar, body: dict[str, Any], headers: dict[str, str]) -> tuple[int, Any]:
    """PATCH the character, returning the status and the JSON body, if any."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/characters/{char.id}", json=body, headers=headers)
    return response.status_code, response.json() if response.content else None


async def reload(char: VChar) -> VChar:
    """The character as the database has it."""
    saved = await VChar.get(char.id)
    assert saved is not None
    return saved


@pytest.mark.parametrize("owner,storyteller", [(True, False), (False, True)])
async def test_edit_character_allowed(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    owner: bool,
    storyteller: bool,
):
    """Owners and Storytellers can save, and get 204 with no body."""
    char = await make_saved_char(user_id=TEST_USER_ID if owner else 999999)
    mock_char_mgr_fetchid.return_value = char

    with patch.object(
        routes_module, "is_storyteller", new_callable=AsyncMock, return_value=storyteller
    ):
        status, data = await patch_char(char, edit_body(char, humanity=5), auth_headers)

    assert status == 204
    assert data is None
    assert (await reload(char)).raw_humanity == 5


async def test_edit_character_public_access_forbidden(
    auth_headers: dict[str, str], edit_guild: MockGuild, mock_char_mgr_fetchid: MockAsyncFn
):
    """A guild member with only public access gets 403, and nothing changes."""
    char = await make_saved_char(user_id=999999)
    mock_char_mgr_fetchid.return_value = char

    with patch.object(routes_module, "is_storyteller", new_callable=AsyncMock, return_value=False):
        status, _ = await patch_char(char, edit_body(char, humanity=5), auth_headers)

    assert status == 403
    assert (await reload(char)).raw_humanity == 7


async def test_edit_character_non_member(
    auth_headers: dict[str, str], mock_bot: MockBot, mock_char_mgr_fetchid: MockAsyncFn
):
    """Someone outside the character's guild gets 404."""
    await populate_guild_cache([make_mock_guild(TEST_GUILD_ID, "Test Guild", user_is_member=False)])
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    status, _ = await patch_char(char, edit_body(char), auth_headers)

    assert status == 404


async def test_edit_character_writes_fields(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """Every field is written, normalized, without wiping Stains or touching
    the Chronicle log or experience."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    stored = await reload(char)  # Mongo truncates timestamps to milliseconds
    body = edit_body(
        char,
        name="  Nadea   Vex ",
        health="x/..//.",
        willpower="...x",
        humanity=6,
        stains=2,
        potency=3,
        hunger=4,
        convictions=["  Never  shun pain. ", "", "Only kill in sacrifice."],
        profile={"description": "Tall.", "biography": "Born."},
    )

    status, _ = await patch_char(char, body, auth_headers)

    assert status == 204
    saved = await reload(char)
    assert saved.raw_name == "Nadea Vex"
    assert saved.health == "...///x"
    assert saved.willpower == "...x"
    assert saved.raw_humanity == 6
    assert saved.stains == 2
    assert saved.potency == 3
    assert saved.raw_hunger == 4
    assert saved.convictions == ["Never shun pain.", "Only kill in sacrifice."]
    assert saved.profile.description == "Tall."
    assert saved.profile.biography == "Born."
    assert saved.log == stored.log
    assert saved.experience == stored.experience


async def test_edit_character_unknown_field(
    auth_headers: dict[str, str], edit_guild: MockGuild, mock_char_mgr_fetchid: MockAsyncFn
):
    """Unknown fields are a 422, and nothing is written."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    status, data = await patch_char(char, edit_body(char, humanity=5, splat="mortal"), auth_headers)

    assert status == 422
    assert data["detail"][0]["loc"] == ["body", "splat"]
    saved = await reload(char)
    assert saved.raw_humanity == 7
    assert saved.splat == "vampire"


async def test_edit_character_unknown_profile_field(
    auth_headers: dict[str, str], edit_guild: MockGuild, mock_char_mgr_fetchid: MockAsyncFn
):
    """Profile images aren't editable here."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    profile = {"description": "", "biography": "", "images": ["http://x.png"]}

    status, data = await patch_char(char, edit_body(char, profile=profile), auth_headers)

    assert status == 422
    assert data["detail"][0]["loc"] == ["body", "profile", "images"]


async def test_edit_character_traits(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """Missing Disciplines and custom traits are deleted, new ones added,
    missing core traits restored without specialties, and attribute
    specialties may be removed. The result is sorted."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    added = [
        {"name": "Auspex", "rating": 1, "type": "discipline", "subtraits": ["Sense"]},
        {"name": "Baking", "rating": 2, "type": "custom", "subtraits": []},
    ]
    traits = body_traits(
        char,
        drop=("Potence", "Cooking", "Athletics", "Dexterity"),
        add=added,
        Strength={"subtraits": []},
    )

    status, _ = await patch_char(char, edit_body(char, traits=traits), auth_headers)

    assert status == 204
    saved = {t.name: t for t in (await reload(char)).raw_traits}
    assert "Potence" not in saved
    assert "Cooking" not in saved
    assert saved["Auspex"].raw_subtraits == ["Sense"]
    assert saved["Baking"].rating == 2
    assert saved["Athletics"].rating == 0
    assert saved["Athletics"].raw_subtraits == []
    assert saved["Dexterity"].rating == 1
    assert saved["Strength"].raw_subtraits == []
    names = [t.name for t in (await reload(char)).raw_traits]
    assert names == sorted(names, key=str.casefold)


async def test_edit_character_attribute_specialty_added(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """Attributes can't gain specialties; the error points at the trait."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    traits = body_traits(char, Strength={"subtraits": ["Lifting", "Throwing"]})
    index = next(i for i, t in enumerate(traits) if t["name"] == "Strength")

    status, data = await patch_char(char, edit_body(char, traits=traits), auth_headers)

    assert status == 422
    assert data["detail"][0]["loc"] == ["body", "traits", index, "subtraits"]


async def test_edit_character_core_trait_retyped(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """A core Attribute can't be sent as another type, nor a new trait as an
    Attribute."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    new_attr = {"name": "Luck", "rating": 2, "type": "attribute", "subtraits": []}
    traits = body_traits(char, add=[new_attr], Strength={"type": "custom"})

    status, data = await patch_char(char, edit_body(char, traits=traits), auth_headers)

    assert status == 422
    locs = [error["loc"] for error in data["detail"]]
    assert ["body", "traits", len(traits) - 1, "type"] in locs
    assert len(locs) == 2


async def test_edit_character_duplicate_trait(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """Trait names must be unique, ignoring case."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    dupe = {"name": "cooking", "rating": 1, "type": "custom", "subtraits": []}
    traits = body_traits(char, add=[dupe])

    status, data = await patch_char(char, edit_body(char, traits=traits), auth_headers)

    assert status == 422
    assert data["detail"][0]["loc"] == ["body", "traits", len(traits) - 1, "name"]


@pytest.mark.parametrize(
    "new_name,taken,status", [("Other", True, 422), ("NADEA theron", True, 204)]
)
async def test_edit_character_name_uniqueness(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    new_name: str,
    taken: bool,
    status: int,
):
    """A name another character has is a 422; changing capitalization is fine."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    with patch.object(char_mgr, "has_character", new_callable=AsyncMock, return_value=taken):
        result, data = await patch_char(char, edit_body(char, name=new_name), auth_headers)

    assert result == status
    if status == 422:
        assert data["detail"][0]["loc"] == ["body", "name"]
    else:
        assert (await reload(char)).raw_name == new_name


@pytest.mark.parametrize(
    "splat,overrides,loc",
    [
        (VCharSplat.MORTAL, {"potency": 1}, "potency"),
        (VCharSplat.GHOUL, {"hunger": 1}, "hunger"),
        (VCharSplat.THIN_BLOOD, {"potency": 3}, "potency"),
        (VCharSplat.VAMPIRE, {"hunger": None}, "hunger"),
        (VCharSplat.VAMPIRE, {"health": "..."}, "health"),
        (VCharSplat.VAMPIRE, {"willpower": "..?.."}, "willpower"),
        (VCharSplat.VAMPIRE, {"stains": 11}, "stains"),
        (VCharSplat.VAMPIRE, {"convictions": ["a", "b", "c", "d"]}, "convictions"),
    ],
)
async def test_edit_character_invalid_fields(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    splat: VCharSplat,
    overrides: dict[str, Any],
    loc: str,
):
    """Invalid values are a 422 pointing at the field."""
    char = await make_saved_char(splat=splat)
    mock_char_mgr_fetchid.return_value = char
    body = {k: v for k, v in edit_body(char, **overrides).items() if v is not None}

    status, data = await patch_char(char, body, auth_headers)

    assert status == 422
    assert data["detail"][0]["loc"] == ["body", loc]


async def test_edit_character_mortal(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """Mortals save without Potency or Hunger."""
    char = await make_saved_char(splat=VCharSplat.MORTAL)
    mock_char_mgr_fetchid.return_value = char

    status, _ = await patch_char(char, edit_body(char, humanity=8), auth_headers)

    assert status == 204
    assert (await reload(char)).raw_humanity == 8


async def test_edit_character_posts_update(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    update_channel: MockChannel,
):
    """The update channel gets a summary of the changes."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    added = {"name": "Auspex", "rating": 1, "type": "discipline", "subtraits": []}
    traits = body_traits(char, drop=("Cooking",), add=[added], Athletics={"rating": 3})
    body = edit_body(char, health="....//", humanity=6, traits=traits)

    status, _ = await patch_char(char, body, auth_headers)

    assert status == 204
    update_channel.send.assert_awaited_once()
    embed: discord.Embed = update_channel.send.call_args.kwargs["embed"]
    assert embed.title == "Character Updated"
    assert embed.description is not None
    for line in (
        "Set Superficial Health damage to `2`.",
        "Set Humanity to `6`.",
        "Added `Auspex`: `1`.",
        "Removed `Cooking`.",
        "Set `Athletics` to `3`.",
    ):
        assert line in embed.description


async def test_edit_character_no_changes_no_post(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    update_channel: MockChannel,
):
    """Saving an unchanged sheet posts nothing."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    status, _ = await patch_char(char, edit_body(char), auth_headers)

    assert status == 204
    update_channel.send.assert_not_awaited()


async def test_edit_character_post_failure(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    update_channel: MockChannel,
):
    """A failed update post doesn't fail the saved edit."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    update_channel.send.side_effect = discord.HTTPException(MagicMock(status=500), "Oops")

    status, _ = await patch_char(char, edit_body(char, humanity=5), auth_headers)

    assert status == 204
    assert (await reload(char)).raw_humanity == 5


async def test_edit_character_publishes_once(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """The "changed" event goes out once."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    with patch.object(char_events, "publish") as publish:
        status, _ = await patch_char(char, edit_body(char, humanity=5), auth_headers)

    assert status == 204
    publish.assert_called_once_with(char.id_str)


@pytest.mark.parametrize("potency,status", [(3, 204), (4, 422)])
async def test_edit_thin_blood_existing_potency(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    potency: int,
    status: int,
):
    """Discord allows thin-bloods any Potency, so one over 2 may be kept, but
    not raised."""
    char = await make_saved_char(splat=VCharSplat.THIN_BLOOD, potency=3)
    mock_char_mgr_fetchid.return_value = char

    result, data = await patch_char(char, edit_body(char, potency=potency), auth_headers)

    assert result == status
    if status == 422:
        assert data["detail"][0]["loc"] == ["body", "potency"]


async def test_edit_long_conviction(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """An existing Conviction over the limit may be kept, but a new one is a
    422 pointing at its slot, blanks included."""
    old = "A" * 300
    char = await make_saved_char(convictions=[old])
    mock_char_mgr_fetchid.return_value = char

    status, _ = await patch_char(char, edit_body(char, convictions=[old, "", ""]), auth_headers)
    assert status == 204
    assert (await reload(char)).convictions == [old]

    body = edit_body(char, convictions=[old, "", "B" * 201])
    status, data = await patch_char(char, body, auth_headers)
    assert status == 422
    assert data["detail"][0]["loc"] == ["body", "convictions", 2]


async def test_edit_rename_sorts_after_save(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """A rename re-sorts the character lists once it's saved."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    with patch.object(char_mgr, "sort_chars", new_callable=AsyncMock) as sort_chars:
        status, _ = await patch_char(char, edit_body(char, name="Abe"), auth_headers)

    assert status == 204
    sort_chars.assert_awaited_once()


async def test_edit_failed_save_rolls_back(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
):
    """A failed save restores the cached character and doesn't re-sort."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char

    with (
        patch.object(char_mgr, "sort_chars", new_callable=AsyncMock) as sort_chars,
        patch.object(VChar, "save_changes", side_effect=RuntimeError("Mongo down")),
        pytest.raises(RuntimeError),
    ):
        await patch_char(char, edit_body(char, name="Abe"), auth_headers)

    assert char.raw_name == "Nadea Theron"
    sort_chars.assert_not_awaited()


async def test_edit_posts_without_gateway_member(
    auth_headers: dict[str, str],
    edit_guild: MockGuild,
    mock_char_mgr_fetchid: MockAsyncFn,
    no_duplicates: MockAsyncFn,
    update_channel: MockChannel,
):
    """The update post comes from the guild cache, so it doesn't need the
    editor in the gateway's member cache."""
    char = await make_saved_char()
    mock_char_mgr_fetchid.return_value = char
    edit_guild.get_member.side_effect = None
    edit_guild.get_member.return_value = None

    status, _ = await patch_char(char, edit_body(char, humanity=5), auth_headers)

    assert status == 204
    embed: discord.Embed = update_channel.send.call_args.kwargs["embed"]
    assert embed.description is not None
    assert embed.description.startswith(f"__<@{TEST_USER_ID}> updated")
    assert embed.author is not None
    assert embed.author.icon_url == "http://avatar.png"
