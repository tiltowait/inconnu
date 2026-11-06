"""Fixtures shared by the Rolepost tests."""

from collections.abc import Callable, Generator
from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId
from beanie.odm.queries.find import FindMany
from pydantic import AnyUrl
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.command_cursor import AsyncCommandCursor

import db
from bot import InconnuBot
from ctx import AppCtx
from models import RPPost
from models.rpheader import DamageSubdoc, HeaderSubdoc

type MockCollection = AsyncMock
type MockCtx = MagicMock
type MockFind = MagicMock
type PostFactory = Callable[..., RPPost]
type SetResults = Callable[[list[dict[str, Any]]], None]

GUILD_ID = 1000
USER_ID = 2000
VISIBLE_CHANNEL_ID = 3000


@pytest.fixture(autouse=True)
def mock_avatars() -> Generator[None]:
    """Avoids building real avatar URLs."""
    url = "https://example.com/avatar.png"
    with ExitStack() as stack:
        for module in ("bookmarks", "post", "search", "tags"):
            stack.enter_context(patch(f"inconnu.roleplay.{module}.get_avatar", return_value=url))
        yield


@pytest.fixture
def rp_ctx() -> MockCtx:
    """A command context for the test user."""
    ctx = MagicMock(spec=AppCtx)
    channel = MagicMock(spec=discord.TextChannel, id=VISIBLE_CHANNEL_ID)
    channel.permissions_for.return_value = discord.Permissions(
        view_channel=True, read_message_history=True
    )
    ctx.guild = MagicMock(spec=discord.Guild, id=GUILD_ID, channels=[channel])
    ctx.guild_id = GUILD_ID
    ctx.user = MagicMock(spec=discord.Member, id=USER_ID, display_name="Author")
    ctx.user.mention = f"<@{USER_ID}>"
    ctx.bot = MagicMock(spec=InconnuBot)
    ctx.bot.cmd_mention.return_value = "</post:1>"
    ctx.interaction = AsyncMock(spec=discord.Interaction)
    ctx.respond = AsyncMock()
    ctx.send_modal = AsyncMock()
    return ctx


@pytest.fixture
def show_error() -> Generator[AsyncMock]:
    """The error shown to the user."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def make_post() -> PostFactory:
    """Makes unsaved Roleposts."""

    def factory(content="The post content", **kwargs: Any) -> RPPost:
        """Make a Rolepost."""
        damage = DamageSubdoc(superficial=0, aggravated=0)
        header = HeaderSubdoc(
            charid=PydanticObjectId(),
            char_name="Nadea",
            blush=-1,
            hunger=1,
            location="",
            merits="",
            flaws="",
            temp="",
            health=damage,
            willpower=damage,
        )
        defaults: dict[str, Any] = {
            "guild": GUILD_ID,
            "channel": VISIBLE_CHANNEL_ID,
            "user": USER_ID,
            "message_id": 4000,
            "url": AnyUrl("https://discord.com/channels/1000/3000/4000"),
        }
        return RPPost(header=header, content=content, **(defaults | kwargs))

    return factory


@pytest.fixture
def find() -> Generator[MockFind]:
    """RPPost.find(), which finds nothing unless told otherwise through
    find.return_value.__aiter__."""
    query = MagicMock(spec=FindMany)
    query.sort.return_value = query
    query.limit.return_value = query
    query.__aiter__.return_value = []
    with patch.object(RPPost, "find", return_value=query) as mock:
        yield mock


@pytest.fixture
def rp_posts() -> Generator[MockCollection]:
    """The raw Rolepost collection."""
    collection = AsyncMock(spec=AsyncCollection)
    with patch.object(db, "rp_posts", collection):
        yield collection


@pytest.fixture
def set_results(rp_posts: MockCollection) -> SetResults:
    """Sets the documents the collection's aggregate() returns."""

    def setter(documents: list[dict[str, Any]]):
        """Set the aggregation's results."""
        cursor = MagicMock(spec=AsyncCommandCursor)
        cursor.__aenter__.return_value = cursor
        cursor.__aiter__.return_value = documents
        rp_posts.aggregate.return_value = cursor

    return setter
