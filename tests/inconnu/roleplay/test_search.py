"""Tests for inconnu/roleplay/search.py."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from beanie.odm.queries.find import FindMany

from ctx import AppCtx
from inconnu.roleplay.search import SortOrder, search
from models import RPPost


async def found_posts() -> AsyncGenerator[RPPost]:
    """A query result with a single post."""
    post = MagicMock(spec=RPPost)
    post.utc_date = datetime(2026, 1, 1, tzinfo=UTC)
    post.content = "The post content"
    post.url = "https://discord.com/channels/1/2/3"
    yield cast(RPPost, post)


async def test_footer_names_mentioned_user():
    """The footer names the mentioned member, not the post's author."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild_id = 1
    ctx.respond = AsyncMock()
    author = MagicMock(spec=discord.Member, id=2, display_name="Author")
    mentioned = MagicMock(spec=discord.Member, id=3, display_name="Mentioned")

    query = MagicMock(spec=FindMany)
    query.sort.return_value = query
    query.limit.return_value = found_posts()

    with (
        patch.object(RPPost, "find", return_value=query),
        patch("inconnu.roleplay.search.get_avatar", return_value="https://example.com/a.png"),
    ):
        await search(
            ctx,
            author,
            needle=None,
            character=None,
            mentioning=mentioned,
            after=None,
            before=None,
            ephemeral=True,
            summary=True,
            sort_order=SortOrder.NEWEST.value,
        )

    embed = ctx.respond.await_args.kwargs["embed"]
    assert embed.footer.text == "Mentioning Mentioned"
