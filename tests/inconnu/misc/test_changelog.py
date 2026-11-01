"""Tests for inconnu/misc/changelog.py."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from inconnu.misc.changelog import (
    PAGE_SIZE,
    RELEASES_URL,
    ReleaseInfo,
    build_changelog,
    compact_text,
    fetch_changelog,
    show_changelog,
    split_sections,
)
from ui.views import PagedView

PUBLISHED = datetime(2026, 10, 31, tzinfo=UTC)
COMMANDS = {"vr", "changelog"}

type MockBot = MagicMock
type MockCtx = MagicMock


@pytest.mark.parametrize(
    "text,expected",
    [
        ("## Fixes\n\n- A fix", "## Fixes\n- A fix"),
        ("- A fix\n\n## Features", "- A fix\n## Features"),
        ("# v1.0\n\n## Fixes\n\n- A fix", "# v1.0\n## Fixes\n- A fix"),
        ("- One\n\n### Sub\n\n- Two", "- One\n### Sub\n- Two"),
        ("First paragraph\n\nSecond paragraph", "First paragraph\n\nSecond paragraph"),
        ("#hashtag\n\ntext", "#hashtag\n\ntext"),
        ("- A fix\n\n\n## Features\n\n\n- A feature", "- A fix\n## Features\n- A feature"),
        ("## Fixes\r\n\r\n- A fix\r\n\r\n## Features", "## Fixes\n- A fix\n## Features"),
        ("One\r\n\r\nTwo", "One\n\nTwo"),
        ("No headings here", "No headings here"),
        ("", ""),
    ],
)
def test_compact_text(text: str, expected: str):
    """Blank lines around headings are removed; others are kept."""
    assert compact_text(text) == expected


def test_split_sections():
    """Each "##" heading starts a new, compacted section."""
    text = "## Fixes\n\n- A fix\n\n## Features\n\n- A feature\n\nMore detail"

    assert split_sections(text) == [
        "## Fixes\n- A fix",
        "## Features\n- A feature\n\nMore detail",
    ]


def test_split_sections_crlf():
    """Windows line endings split like Unix ones."""
    text = "## Fixes\r\n\r\n- A fix\r\n\r\n## Features\r\n- A feature"
    assert split_sections(text) == ["## Fixes\n- A fix", "## Features\n- A feature"]


def test_split_sections_preamble():
    """Text before the first "##" heading is its own section."""
    text = "Summary\n\n## Fixes\n- A fix"
    assert split_sections(text) == ["Summary", "## Fixes\n- A fix"]


def test_split_sections_other_headings():
    """Only "##" headings split; "#" and "###" stay in their section."""
    text = "# v1.0\n## Fixes\n### Dice\n- A fix\n#### Detail"

    assert split_sections(text) == ["# v1.0", "## Fixes\n### Dice\n- A fix\n#### Detail"]


def test_split_sections_no_headings():
    """Text without headings is a single section."""
    assert split_sections("- A fix\n\n- Another") == ["- A fix\n\n- Another"]


# build_changelog


def mention(name: str) -> str:
    """A realistic command mention, much longer than `/name`."""
    return f"</{name}:1234567890123456789>"


def make_bot() -> MockBot:
    """A bot that knows the COMMANDS."""
    bot = MagicMock(spec=InconnuBot)
    bot.cmd_mention.side_effect = lambda name: mention(name) if name in COMMANDS else None
    return bot


def make_release(text: str) -> ReleaseInfo:
    """Make a release with the given notes."""
    return ReleaseInfo(tag="v2026.10.31", text=text, published_at=PUBLISHED)


def page_items(view: PagedView) -> list[dict[str, Any]]:
    """The shown page's top-level items, without the page controls."""
    return [
        item
        for item in view.to_components()
        if item["type"] != discord.ComponentType.action_row.value
    ]


def section_texts(view: PagedView) -> list[str]:
    """The text of each section container on the shown page."""
    return [
        item["components"][0]["content"]
        for item in page_items(view)
        if item["type"] == discord.ComponentType.container.value
    ]


async def test_build_changelog_layout():
    """The title and date lead, each section is its own container, and the
    releases link comes last."""
    view = build_changelog(
        make_bot(), make_release("## Fixes\n\n- A fix\n\n## Features\n\n- A feature")
    )
    items = page_items(view)

    assert [item["type"] for item in items] == [
        discord.ComponentType.text_display.value,
        discord.ComponentType.text_display.value,
        discord.ComponentType.container.value,
        discord.ComponentType.container.value,
        discord.ComponentType.section.value,
    ]
    assert items[0]["content"] == "# Inconnu v2026.10.31"
    assert items[1]["content"] == f"-# Released <t:{int(PUBLISHED.timestamp())}:D>"
    assert section_texts(view) == ["## Fixes\n- A fix", "## Features\n- A feature"]
    assert items[-1]["accessory"]["url"] == RELEASES_URL
    assert items[-1]["components"][0]["content"] == "\u200b"


async def test_build_changelog_pages():
    """Long notes are split across pages, each with the title and link, in order."""
    lines = [f"- Fix {i:03} " + "x" * 90 for i in range(100)]
    text = "## Fixes\n" + "\n".join(lines[:50]) + "\n## Features\n" + "\n".join(lines[50:])
    view = build_changelog(make_bot(), make_release(text))

    assert len(view.pages) > 1
    shown = []
    for index in range(len(view.pages)):
        if index > 0:
            await view.next_page(AsyncMock(spec=discord.Interaction))
        items = page_items(view)
        assert items[0]["content"] == "# Inconnu v2026.10.31"
        assert items[-1]["accessory"]["url"] == RELEASES_URL
        texts = section_texts(view)
        assert sum(map(len, texts)) <= PAGE_SIZE
        shown += [line for text in texts for line in text.splitlines()]

    assert shown == text.splitlines()


async def test_build_changelog_note():
    """A note goes beside the releases link on every page."""
    text = "## Fixes\n" + "\n".join(f"- Fix {i:03} " + "x" * 90 for i in range(100))
    view = build_changelog(make_bot(), make_release(text), note="-# A note")

    assert len(view.pages) > 1
    for index in range(len(view.pages)):
        if index > 0:
            await view.next_page(AsyncMock(spec=discord.Interaction))
        link = page_items(view)[-1]
        assert link["components"][0]["content"] == "-# A note"
        assert link["accessory"]["url"] == RELEASES_URL


async def test_build_changelog_mentions():
    """`/command` text in the notes and the note becomes a mention."""
    text = "## Fixes\n- `/vr` rolls correctly\n- `/unknown` is left alone"
    view = build_changelog(make_bot(), make_release(text), note="Use `/changelog`")
    items = page_items(view)

    assert section_texts(view) == [
        f"## Fixes\n- {mention('vr')} rolls correctly\n- `/unknown` is left alone"
    ]
    assert items[-1]["components"][0]["content"] == f"Use {mention('changelog')}"


async def test_build_changelog_pages_fit_mentions():
    """Pages are sized after mentions are substituted, so they stay in bounds."""
    text = "## Fixes\n" + "\n".join(f"- Use `/vr` {i:03} " + "x" * 20 for i in range(200))
    view = build_changelog(make_bot(), make_release(text))

    for index in range(len(view.pages)):
        if index > 0:
            await view.next_page(AsyncMock(spec=discord.Interaction))
        texts = section_texts(view)
        assert sum(map(len, texts)) <= PAGE_SIZE
        assert all("`/vr`" not in text for text in texts)


@pytest.mark.parametrize("text", ["", " \n\n "])
async def test_build_changelog_without_notes(text: str):
    """A release without notes says so, rather than sending empty text."""
    view = build_changelog(make_bot(), make_release(text))
    assert section_texts(view) == ["*No release notes.*"]


# fetch_changelog


@pytest.fixture
async def mock_github() -> AsyncGenerator[MagicMock]:
    """GitHub's latest-release response, patched. Set .json.return_value."""
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.json = AsyncMock()
    session = MagicMock(spec=aiohttp.ClientSession)
    session.get.return_value.__aenter__.return_value = response

    fetch_changelog.cache_clear()
    with patch.object(aiohttp, "ClientSession") as client_session:
        client_session.return_value.__aenter__.return_value = session
        yield response
    fetch_changelog.cache_clear()


@pytest.mark.parametrize("body,expected", [("## Fixes\n- A fix", "## Fixes\n- A fix"), (None, "")])
async def test_fetch_changelog(mock_github: MagicMock, body: str | None, expected: str):
    """The latest release is parsed; a release without notes has empty text."""
    mock_github.json.return_value = {
        "tag_name": "v2026.11.01",
        "body": body,
        "published_at": "2026-11-01T00:00:00Z",
    }

    assert await fetch_changelog() == ReleaseInfo(
        tag="v2026.11.01", text=expected, published_at=datetime(2026, 11, 1, tzinfo=UTC)
    )


# show_changelog


@pytest.fixture
def ctx() -> MockCtx:
    """The /changelog invocation."""
    ctx = MagicMock(spec=AppCtx)
    ctx.bot = make_bot()
    # A property on ApplicationContext, so the spec can't infer it
    ctx.respond = AsyncMock()
    return ctx


@pytest.mark.parametrize("hidden", [True, False])
async def test_show_changelog(ctx: MockCtx, hidden: bool):
    """The latest release is shown as a paged view."""
    release = make_release("## Fixes\n- A fix")
    with patch("inconnu.misc.changelog.fetch_changelog", AsyncMock(return_value=release)):
        await show_changelog(ctx, hidden)

    kwargs = ctx.respond.call_args.kwargs
    assert kwargs["ephemeral"] == hidden
    assert section_texts(kwargs["view"]) == ["## Fixes\n- A fix"]


@pytest.mark.parametrize("error", [aiohttp.ClientError(), KeyError("body")])
async def test_show_changelog_fetch_error(ctx: MockCtx, error: Exception):
    """A failed fetch shows an error instead."""
    with (
        patch("inconnu.misc.changelog.fetch_changelog", AsyncMock(side_effect=error)),
        patch("inconnu.misc.changelog.ui.embeds.error", AsyncMock()) as mock_error,
    ):
        await show_changelog(ctx, True)

    mock_error.assert_awaited_once_with(ctx, "Unable to fetch changelog.")
    ctx.respond.assert_not_awaited()
