"""Run tests against the website."""

from datetime import datetime
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pydantic import AnyUrl
from pymongo import AsyncMongoClient

from inconnu.constants import Damage
from models.rpheader import DamageSubdoc, HeaderSubdoc
from models.rppost import PostHistoryEntry, RPPost
from models.vchar import VChar
from server import app

# Static test data IDs

CHAR_ID_1 = PydanticObjectId("6140d7d811c1853b3d42c1e9")
CHAR_ID_2 = PydanticObjectId("613d3e4bba8a6a8dc0ee2a09")
CHAR_ID_MISSING = PydanticObjectId("613d3e4bba8a6a8dc0ee2a06")

POST_ID_1 = PydanticObjectId("6404dfafa9b47c1a4dd13294")
POST_ID_MISSING = PydanticObjectId("6367ee5eaa29004c72953016")


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


@pytest.fixture
async def character1():
    """Create first test character with multiple images."""
    char = VChar(
        id=CHAR_ID_1,
        guild=123456789,
        user=987654321,
        name="Test Character 1",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    char.profile.images = [
        "https://example.com/img1.jpg",
        "https://example.com/img2.jpg",
        "https://example.com/img3.jpg",
    ]
    char.profile.biography = "Test biography"
    char.profile.description = "Test description"
    await char.insert()
    return char


@pytest.fixture
async def character2():
    """Create second test character with single image."""
    char = VChar(
        id=CHAR_ID_2,
        guild=123456789,
        user=111111111,
        name="Test Character 2",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    char.profile.images = ["https://example.com/portrait.jpg"]
    char.profile.biography = "Another test bio"
    await char.insert()
    return char


@pytest.fixture
async def rolepost(request):
    """Create rolepost with history (deleted or normal based on parameter)."""
    # Get the 'use_deleted' parameter from the test
    use_deleted = request.param if hasattr(request, "param") else False

    base_date = datetime(2023, 3, 5, 12, 0, 0)

    # Create header subdoc
    header = HeaderSubdoc(
        charid=CHAR_ID_1,
        char_name="Test Character",
        blush=0,
        hunger=3,
        location="Downtown",
        merits="Iron Will",
        flaws="Dark Secret",
        temp="",
        health=DamageSubdoc(superficial=0, aggravated=0),
        willpower=DamageSubdoc(superficial=1, aggravated=0),
    )

    # Create post with 6 history entries (7 total versions)
    history = [
        PostHistoryEntry(
            content=f"Version {i}",
            date=datetime(2023, 3, 5, 12 + i, 0, 0),
        )
        for i in range(6, 0, -1)  # 6 down to 1
    ]

    post = RPPost(
        id=POST_ID_1,
        guild=123456789,
        channel=111111111,
        user=987654321,
        message_id=222222222,
        content="Latest version (7)",
        date=base_date,
        date_modified=datetime(2023, 3, 5, 18, 0, 0),
        header=header,
        url=AnyUrl("https://discord.com/channels/123456789/111111111/222222222"),
        deleted=use_deleted,
        deletion_date=datetime(2023, 3, 6, 10, 0, 0) if use_deleted else None,
        history=history,
    )
    await post.insert()
    return post


@pytest.fixture
def mock_discord():
    """Mock Discord bot, guild, channel, and user objects."""
    # Mock user
    mock_user = MagicMock()
    mock_user.name = "TestUser"
    mock_user.display_name = "Test User"
    mock_user.id = 987654321

    # Mock channel
    mock_channel = MagicMock()
    mock_channel.name = "roleplay"
    mock_channel.id = 111111111

    # Mock guild
    mock_guild = MagicMock()
    mock_guild.name = "Test Server"
    mock_guild.id = 123456789
    mock_guild.get_member = MagicMock(return_value=mock_user)
    mock_guild.get_channel = MagicMock(return_value=mock_channel)

    # Mock bot
    mock_bot = MagicMock()
    mock_bot.user = mock_user
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    return mock_bot


@pytest.mark.parametrize(
    "charid,expected_status,use_char1,use_char2",
    [
        ("6140d7d811c1853b3d42c1e9", 200, True, False),  # character1
        ("613d3e4bba8a6a8dc0ee2a09", 200, False, True),  # character2
        ("Invalid", 400, False, False),  # Invalid ID
        ("613d3e4bba8a6a8dc0ee2a06", 404, False, False),  # Missing
    ],
)
async def test_profile_page(
    charid: str,
    expected_status: int,
    use_char1: bool,
    use_char2: bool,
    character1,
    character2,
    mock_discord,
):
    """Test character profile page rendering."""
    with patch("bot.bot", mock_discord):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/profile/{charid}")
            assert r.status_code == expected_status

            if expected_status != 200:
                res = r.json()
                if expected_status == 400:
                    assert res["detail"] == "Invalid ID."
                elif expected_status == 404:
                    assert res["detail"] == "Character not found."
                else:
                    pytest.fail(f"Unexpected response code: {r.status_code}")
            else:
                # Verify carousel items match image count
                if use_char1:
                    expected_images = len(character1.profile.images)
                elif use_char2:
                    expected_images = len(character2.profile.images)
                else:
                    pytest.fail("Expected to use char1 or char2")

                assert r.text.count("carousel-item") == expected_images


@pytest.mark.parametrize(
    "postid,expected_status,rolepost,num_posts",
    [
        ("6404dfafa9b47c1a4dd13294", 200, False, 7),  # Normal post
        ("6404dfafa9b47c1a4dd13294", 200, True, 7),  # Deleted post
        ("6367ee5eaa29004c72953016", 404, False, 0),  # Missing post
        ("Invalid", 400, False, 0),  # Invalid ID
    ],
    indirect=["rolepost"],  # Tell pytest to pass the 3rd param to the rolepost fixture
)
async def test_posts_page(
    postid: str,
    expected_status: int,
    rolepost,
    num_posts: int,
    mock_discord,
):
    """Test rolepost history page rendering."""
    with patch("bot.bot", mock_discord):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/post/{postid}")
            assert r.status_code == expected_status

            if expected_status != 200:
                res = r.json()
                if expected_status == 400:
                    assert res["detail"] == "Invalid ID."
                elif expected_status == 404:
                    assert res["detail"] == "Post not found."
                else:
                    pytest.fail(f"Unexpected response code: {r.status_code}")
            else:
                use_deleted = rolepost.deleted if rolepost else False
                if use_deleted:
                    assert "Deleted" in r.text
                if num_posts == 1:
                    assert r.text.count("dropdown-item") == 0
                else:
                    assert r.text.count("dropdown-item") == num_posts
