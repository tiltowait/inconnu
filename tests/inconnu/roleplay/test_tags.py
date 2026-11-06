"""Tests for inconnu/roleplay/tags.py."""

from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest
from discord.ext.pages import Page, Paginator

from inconnu.roleplay.tags import TagView, show_tags
from tests.inconnu.roleplay.conftest import (
    GUILD_ID,
    USER_ID,
    MockCollection,
    MockCtx,
    MockFind,
    PostFactory,
    SetResults,
)

type MockInteraction = AsyncMock
type MockPaginator = MagicMock


def tag_docs(count: int) -> list[dict[str, str | int]]:
    """Aggregated tag documents."""
    return [{"_id": f"tag{i}", "count": i + 1} for i in range(count)]


def select_of(view: discord.ui.View) -> discord.ui.Select:
    """The view's tag select."""
    return cast(discord.ui.Select, view.children[0])


def select_values(*values: str):
    """Make the select report these as the user's selection."""
    return patch.object(
        discord.ui.Select, "values", new_callable=PropertyMock, return_value=list(values)
    )


@pytest.fixture
def paginator() -> Generator[MockPaginator]:
    """The tags paginator class."""
    with patch("inconnu.roleplay.tags.Paginator", autospec=Paginator) as mock:
        yield mock


@pytest.fixture
def interaction() -> MockInteraction:
    """The select's interaction."""
    mock = AsyncMock(spec=discord.Interaction)
    mock.guild_id = GUILD_ID
    mock.user = MagicMock(spec=discord.Member, id=USER_ID)
    return mock


# Test show_tags


async def test_only_finds_own_tags(
    rp_ctx: MockCtx, rp_posts: MockCollection, set_results: SetResults, show_error: AsyncMock
):
    """The search covers the user's posts on this server, and skips deleted posts."""
    set_results([])

    await show_tags(rp_ctx)

    match = rp_posts.aggregate.call_args.args[0][0]["$match"]
    assert match["deleted"] is False
    assert match["guild"] == GUILD_ID
    assert match["user"] == USER_ID


async def test_no_tags(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator, show_error: AsyncMock
):
    """A user with no tags gets an error explaining how to make them."""
    set_results([])

    await show_tags(rp_ctx)

    assert show_error.call_args.kwargs["title"] == "You have no tags!"
    paginator.assert_not_called()


async def test_page_shows_counts_and_select(
    rp_ctx: MockCtx, set_results: SetResults, paginator: MockPaginator
):
    """A page lists each tag's post count and offers the tags in a select."""
    set_results(tag_docs(2))

    await show_tags(rp_ctx)

    page = cast(Page, paginator.call_args.args[0][0])
    embed = cast(list[discord.Embed], page.embeds)[0]
    assert embed.description == "1: `tag0`\n2: `tag1`"

    select = select_of(cast(discord.ui.View, page.custom_view))
    assert [option.label for option in select.options] == ["tag0", "tag1"]
    assert select.max_values == 2
    assert paginator.return_value.respond.await_args.kwargs["ephemeral"] is True


@pytest.mark.parametrize(
    "tags,pages,controls",
    [(1, 1, False), (25, 1, False), (26, 2, True), (50, 2, True), (51, 3, True)],
)
async def test_pages_fit_select_limit(
    rp_ctx: MockCtx,
    set_results: SetResults,
    paginator: MockPaginator,
    tags: int,
    pages: int,
    controls: bool,
):
    """Pages hold at most 25 tags, the most a select can offer."""
    set_results(tag_docs(tags))

    await show_tags(rp_ctx)

    assert len(paginator.call_args.args[0]) == pages
    assert paginator.call_args.kwargs["show_indicator"] is controls


# Test TagView


async def test_selection_shows_matching_posts(
    interaction: MockInteraction,
    find: MockFind,
    make_post: PostFactory,
    paginator: MockPaginator,
):
    """Selecting a tag shows the user's posts with it, privately."""
    find.return_value.__aiter__.return_value = [make_post("First"), make_post("Second")]
    view = TagView([("tag", 2)])

    with select_values("tag"):
        await view.callback(interaction)

    assert find.call_args.args[0] == {
        "deleted": False,
        "guild": GUILD_ID,
        "user": USER_ID,
        "tags": {"$all": ["tag"]},
    }
    pages = paginator.call_args.kwargs["pages"]
    assert [page.description for page in pages] == ["First", "Second"]
    assert pages[0].footer.text == "Search tag: tag"
    assert paginator.call_args.kwargs["show_indicator"] is True
    assert paginator.return_value.respond.await_args.kwargs["ephemeral"] is True


async def test_selection_shows_newest_first(
    interaction: MockInteraction,
    find: MockFind,
    make_post: PostFactory,
    paginator: MockPaginator,
):
    """Tagged posts are sorted by date, with the newest first."""
    find.return_value.__aiter__.return_value = [make_post()]
    view = TagView([("tag", 1)])

    with select_values("tag"):
        await view.callback(interaction)

    find.return_value.sort.assert_called_once_with("-date")


async def test_multiple_tags_must_all_match(
    interaction: MockInteraction,
    find: MockFind,
    make_post: PostFactory,
    paginator: MockPaginator,
):
    """Selecting several tags finds posts with all of them."""
    find.return_value.__aiter__.return_value = [make_post()]
    view = TagView([("one", 1), ("two", 1)])

    with select_values("one", "two"):
        await view.callback(interaction)

    assert find.call_args.args[0]["tags"] == {"$all": ["one", "two"]}
    assert paginator.call_args.kwargs["pages"][0].footer.text == "Search tags: one; two"
    assert paginator.call_args.kwargs["show_indicator"] is False


async def test_selection_with_no_posts(
    interaction: MockInteraction,
    find: MockFind,
    paginator: MockPaginator,
    show_error: AsyncMock,
):
    """A selection nothing matches gets an error naming the tags."""
    view = TagView([("one", 1), ("two", 1)])

    with select_values("one", "two"):
        await view.callback(interaction)

    assert show_error.call_args.args[1] == "No posts with tags `one` and `two` found."
    paginator.assert_not_called()
