"""Tests for inconnu/roleplay/bookmarks.py."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext.pages import Paginator

from inconnu.roleplay.bookmarks import show_bookmarks
from tests.inconnu.roleplay.conftest import (
    GUILD_ID,
    USER_ID,
    MockCollection,
    MockCtx,
    SetResults,
)

type MockPaginator = MagicMock

POST_DATE = datetime(2026, 1, 2)  # Mongo returns naive dates


def bookmark(title="A bookmark") -> dict[str, Any]:
    """A bookmark document."""
    return {"title": title, "url": "https://example.com/post", "date": POST_DATE}


@pytest.fixture
def paginator() -> Generator[MockPaginator]:
    """The bookmarks paginator class."""
    with patch("inconnu.roleplay.bookmarks.Paginator", autospec=Paginator) as mock:
        yield mock


async def test_only_finds_own_bookmarks(
    rp_ctx: MockCtx, rp_posts: MockCollection, set_results: SetResults, show_error: AsyncMock
):
    """The search covers the user's posts on this server, and skips deleted posts
    and posts with no title."""
    set_results([])

    await show_bookmarks(rp_ctx)

    match = rp_posts.aggregate.call_args.args[0][0]["$match"]
    assert match == {
        "deleted": False,
        "guild": GUILD_ID,
        "user": USER_ID,
        "title": {"$ne": None},
    }


async def test_no_bookmarks(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator, show_error: AsyncMock
):
    """A user with no bookmarks gets an error explaining how to make them."""
    set_results([])

    await show_bookmarks(rp_ctx)

    assert show_error.call_args.kwargs["title"] == "You have no bookmarks!"
    assert "</post:1>" in show_error.call_args.args[1]
    paginator.assert_not_called()


async def test_bookmark_links_to_post(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator
):
    """A bookmark shows its UTC date and links to the post, privately."""
    set_results([bookmark()])

    await show_bookmarks(rp_ctx)

    date = discord.utils.format_dt(POST_DATE.replace(tzinfo=UTC), "d")
    embed = paginator.call_args.args[0][0]
    assert f"{date}: **[A bookmark](https://example.com/post)**" in embed.description
    assert paginator.return_value.respond.await_args.kwargs["ephemeral"] is True


async def test_one_page_hides_controls(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator
):
    """A single page of bookmarks has no page controls."""
    set_results([bookmark()])

    await show_bookmarks(rp_ctx)

    assert len(paginator.call_args.args[0]) == 1
    assert paginator.call_args.kwargs["show_disabled"] is False
    assert paginator.call_args.kwargs["show_indicator"] is False


async def test_many_bookmarks_paginate(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator
):
    """Bookmarks too long for one embed are split up, with page controls."""
    set_results([bookmark("x" * 128) for _ in range(40)])

    await show_bookmarks(rp_ctx)

    pages = paginator.call_args.args[0]
    assert len(pages) > 1
    assert all(len(page.description) <= 4096 for page in pages)
    assert sum(page.description.count("xxx]") for page in pages) == 40
    assert paginator.call_args.kwargs["show_indicator"] is True
