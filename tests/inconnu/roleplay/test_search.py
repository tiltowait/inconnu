"""Tests for inconnu/roleplay/search.py."""

import re
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext.pages import Paginator
from pymongo import ASCENDING, DESCENDING

from inconnu.roleplay.search import SortOrder, search
from tests.inconnu.roleplay.conftest import (
    GUILD_ID,
    VISIBLE_CHANNEL_ID,
    MockCtx,
    MockFind,
    PostFactory,
)

type MockMember = MagicMock
type MockPaginator = MagicMock

AUTHOR_ID = 2
MENTIONED_ID = 3
TEXT_SCORE = ("content", {"$meta": "textScore"})


async def run_search(ctx: MockCtx, author: MockMember, **options: Any):
    """Run a summary search with the given options."""
    defaults: dict[str, Any] = {
        "needle": None,
        "character": None,
        "mentioning": None,
        "after": None,
        "before": None,
        "ephemeral": True,
        "summary": True,
        "sort_order": SortOrder.MOST_RELEVANT.value,
    }
    await search(ctx, author, **(defaults | options))


@pytest.fixture
def author() -> MockMember:
    """The member whose posts are searched."""
    member = MagicMock(spec=discord.Member, id=AUTHOR_ID, display_name="Author")
    member.mention = f"<@{AUTHOR_ID}>"
    return member


@pytest.fixture
def mentioned() -> MockMember:
    """A member mentioned in a post."""
    member = MagicMock(spec=discord.Member, id=MENTIONED_ID, display_name="Mentioned")
    member.mention = f"<@{MENTIONED_ID}>"
    return member


@pytest.fixture
def paginator() -> Generator[MockPaginator]:
    """The search results paginator class."""
    with patch("inconnu.roleplay.search.Paginator", autospec=Paginator) as mock:
        yield mock


# Test the query


async def test_only_finds_authors_posts(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """The search covers the author's undeleted posts on this server, up to 25."""
    await run_search(rp_ctx, author)

    assert find.call_args.args[0] == {
        "deleted": False,
        "guild": GUILD_ID,
        "user": AUTHOR_ID,
        "channel": {"$in": [VISIBLE_CHANNEL_ID]},
    }
    find.return_value.limit.assert_called_once_with(25)


@pytest.mark.parametrize(
    "view_channel,read_message_history", [(False, True), (True, False), (False, False)]
)
async def test_unreadable_channels_are_excluded(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    show_error: AsyncMock,
    view_channel: bool,
    read_message_history: bool,
):
    """The search skips channels whose history the invoker can't read."""
    hidden = MagicMock(spec=discord.TextChannel, id=VISIBLE_CHANNEL_ID + 1)
    hidden.permissions_for.return_value = discord.Permissions(
        view_channel=view_channel, read_message_history=read_message_history
    )
    rp_ctx.guild.channels.append(hidden)

    await run_search(rp_ctx, author)

    assert find.call_args.args[0]["channel"] == {"$in": [VISIBLE_CHANNEL_ID]}
    hidden.permissions_for.assert_called_once_with(rp_ctx.user)


async def test_own_posts_ignore_channel_visibility(
    rp_ctx: MockCtx, find: MockFind, show_error: AsyncMock
):
    """Users can find their own posts in channels they can no longer see."""
    await run_search(rp_ctx, rp_ctx.user)

    assert "channel" not in find.call_args.args[0]


async def test_no_visible_channels_finds_nothing(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """An invoker who can't see any channels gets no results, rather than all of them."""
    rp_ctx.guild.channels.clear()

    await run_search(rp_ctx, author)

    assert find.call_args.args[0]["channel"] == {"$in": []}


async def test_needle_is_normalized(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    make_post: PostFactory,
):
    """Search text has its spacing normalized, and shows in the footer."""
    find.return_value.__aiter__.return_value = [make_post()]

    await run_search(rp_ctx, author, needle="  two   words ")

    assert find.call_args.args[0]["$text"] == {"$search": "two words"}
    embed = rp_ctx.respond.await_args.kwargs["embed"]
    assert embed.footer.text == "Search key: two words"


async def test_character_filter(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """A character name matches regardless of case."""
    await run_search(rp_ctx, author, character="Nadea")

    assert find.call_args.args[0]["header.char_name"] == re.compile("Nadea", re.IGNORECASE)


async def test_invalid_character_ignored(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """An invalid character name is dropped from the search."""
    await run_search(rp_ctx, author, character="Bad.*Name")

    assert "header.char_name" not in find.call_args.args[0]


async def test_mentioning_filter(
    rp_ctx: MockCtx,
    author: MockMember,
    mentioned: MockMember,
    find: MockFind,
    make_post: PostFactory,
):
    """The search can be limited to a mentioned member, named in the footer."""
    find.return_value.__aiter__.return_value = [make_post()]

    await run_search(rp_ctx, author, mentioning=mentioned)

    assert find.call_args.args[0]["mentions"] == MENTIONED_ID
    embed = rp_ctx.respond.await_args.kwargs["embed"]
    assert embed.footer.text == "Mentioning Mentioned"


@pytest.mark.parametrize(
    "dates,expected",
    [
        ({"after": "2026-01-02"}, {"$gt": datetime(2026, 1, 2)}),
        ({"before": "2026-01-03"}, {"$lt": datetime(2026, 1, 3)}),
        (
            {"after": "2026-01-02", "before": "2026-01-03"},
            {"$gt": datetime(2026, 1, 2), "$lt": datetime(2026, 1, 3)},
        ),
    ],
)
async def test_date_filters(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    show_error: AsyncMock,
    dates: dict[str, str],
    expected: dict[str, datetime],
):
    """Dates limit the search's range."""
    await run_search(rp_ctx, author, **dates)

    assert find.call_args.args[0]["date"] == expected


@pytest.mark.parametrize(
    "dates",
    [{"after": "Yesterday"}, {"after": "2026-01-03", "before": "2026-01-02"}],
)
async def test_bad_dates_stop_search(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    show_error: AsyncMock,
    dates: dict[str, str],
):
    """Bad dates show an error instead of searching."""
    await run_search(rp_ctx, author, **dates)

    assert show_error.call_args.kwargs["title"] == "Invalid date"
    find.assert_not_called()


@pytest.mark.parametrize(
    "order,needle,expected",
    [
        (SortOrder.MOST_RELEVANT, "text", TEXT_SCORE),
        (SortOrder.LEAST_RELEVANT, "text", TEXT_SCORE),
        (SortOrder.MOST_RELEVANT, None, ("date", DESCENDING)),
        (SortOrder.LEAST_RELEVANT, None, ("date", DESCENDING)),
        (SortOrder.NEWEST, "text", ("date", DESCENDING)),
        (SortOrder.OLDEST, "text", ("date", ASCENDING)),
    ],
)
async def test_sort_order(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    show_error: AsyncMock,
    order: SortOrder,
    needle: str | None,
    expected: tuple[str, Any],
):
    """Relevance only applies to text searches; otherwise, newest comes first."""
    await run_search(rp_ctx, author, needle=needle, sort_order=order.value)

    find.return_value.sort.assert_called_once_with(expected)


# Test the results


async def test_summary_previews_posts(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, make_post: PostFactory
):
    """A summary links each post with a short preview, free of punctuation."""
    post = make_post("**Hello**, there!\nThis line is cut off here")
    find.return_value.__aiter__.return_value = [post]

    await run_search(rp_ctx, author, ephemeral=False)

    timestamp = discord.utils.format_dt(post.utc_date, "d")
    kwargs = rp_ctx.respond.await_args.kwargs
    assert kwargs["embed"].description == f"{timestamp}: [Hello there This lin ...]({post.url})"
    assert kwargs["ephemeral"] is False


async def test_least_relevant_reverses_results(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, make_post: PostFactory
):
    """Mongo can't reverse a text score sort, so the results are reversed instead."""
    find.return_value.__aiter__.return_value = [make_post("First"), make_post("Second")]

    await run_search(rp_ctx, author, needle="text", sort_order=SortOrder.LEAST_RELEVANT.value)

    description = rp_ctx.respond.await_args.kwargs["embed"].description
    assert description.index("Second") < description.index("First")


async def test_full_results_paginate(
    rp_ctx: MockCtx,
    author: MockMember,
    find: MockFind,
    make_post: PostFactory,
    paginator: MockPaginator,
):
    """Without summary mode, each post gets a page with a link to it."""
    post = make_post()
    find.return_value.__aiter__.return_value = [post, make_post("Another")]

    await run_search(rp_ctx, author, summary=False, needle="text", ephemeral=False)

    pages = paginator.call_args.args[0]
    assert [page.description for page in pages] == ["The post content", "Another"]
    assert pages[0].title == "Nadea"
    assert pages[0].author.name == "Author"
    assert pages[0].footer.text == "Search key: text"
    assert pages[0].fields[0].value == str(post.url)
    assert paginator.call_args.kwargs["loop_pages"] is True
    respond = paginator.return_value.respond
    assert respond.await_args.args[0] is rp_ctx.interaction
    assert respond.await_args.kwargs["ephemeral"] is False


async def test_no_results_lists_filters(
    rp_ctx: MockCtx,
    author: MockMember,
    mentioned: MockMember,
    find: MockFind,
    show_error: AsyncMock,
):
    """The not found error repeats what was searched for."""
    await run_search(
        rp_ctx,
        author,
        needle="text",
        mentioning=mentioned,
        after="2026-01-02",
        before="2026-01-03",
    )

    message = show_error.call_args.args[1]
    assert show_error.call_args.kwargs["title"] == "Not found"
    assert author.mention in message
    for condition in (
        "Matching `text`",
        f"Mentioning {mentioned.mention}",
        "After `2026-01-02`",
        "Before `2026-01-03`",
    ):
        assert condition in message
    rp_ctx.respond.assert_not_awaited()


async def test_no_results_lists_character(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """The not found error includes the character searched for."""
    await run_search(rp_ctx, author, character="Nadea")

    assert show_error.call_args.args[1] == (
        f"No posts by {author.mention} found with the given search parameters:\n* As `Nadea`."
    )


async def test_no_results_skips_ignored_character(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """An invalid character name wasn't searched for, so it isn't listed."""
    await run_search(rp_ctx, author, character="Bad.*Name")

    assert "Bad.*Name" not in show_error.call_args.args[1]


async def test_no_results_without_filters(
    rp_ctx: MockCtx, author: MockMember, find: MockFind, show_error: AsyncMock
):
    """With nothing to list, the not found error is a plain sentence."""
    await run_search(rp_ctx, author)

    assert show_error.call_args.args[1] == f"No posts by {author.mention} found."
