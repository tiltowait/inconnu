"""Tests for PagedView."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ui import Button, Container, Section, TextDisplay

import services  # noqa: F401 - must load before ui (circular import via utils)
from ui.views import PagedView

PREV = "◀️"
NEXT = "▶️"

type MockInteraction = AsyncMock
type MockUser = MagicMock


def make_view(count: int, author: discord.abc.User | None = None) -> PagedView:
    """Make a view of single-text pages."""
    pages = [[Container(TextDisplay(f"Page {i + 1}"))] for i in range(count)]
    return PagedView(pages, author=author)


def make_user(user_id: int) -> MockUser:
    """Make a mock user with an ID."""
    user = MagicMock(spec=discord.User)
    user.id = user_id
    return user


def make_interaction(user_id: int = 1) -> MockInteraction:
    """Make a mock button-press interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = make_user(user_id)
    return interaction


def page_text(view: PagedView) -> str:
    """The shown page's text."""
    container = view.to_components()[0]
    return container["components"][0]["content"]


def buttons(view: PagedView) -> list[tuple[str | None, str | None, bool]] | None:
    """The page controls as (emoji, label, disabled), if shown."""
    controls = view.to_components()[-1]
    if controls["type"] != discord.ComponentType.action_row.value:
        return None
    return [
        (button.get("emoji", {}).get("name"), button.get("label"), button["disabled"])
        for button in controls["components"]
    ]


async def press(view: PagedView, emoji: str, interaction: MockInteraction | None = None):
    """Press the enabled page control with the given emoji."""
    shown = buttons(view)
    assert shown is not None, "No page controls are shown"
    emojis = [summary[0] for summary in shown]
    index = emojis.index(emoji)
    assert not shown[index][2], f"{emoji!r} is disabled"

    interaction = interaction or make_interaction()
    button = cast(Any, view.children[-1]).children[index]
    await cast(Button, button).callback(interaction)
    interaction.edit.assert_awaited_once_with(view=view)


async def test_no_pages():
    """A view needs pages."""
    with pytest.raises(ValueError):
        PagedView([])


async def test_single_page():
    """One page shows no controls."""
    view = make_view(1)

    assert page_text(view) == "Page 1"
    assert buttons(view) is None


async def test_paging():
    """The controls move between pages and disable at either end."""
    view = make_view(3)
    assert buttons(view) == [(PREV, None, True), (None, "1/3", True), (NEXT, None, False)]

    await press(view, NEXT)
    await press(view, NEXT)
    assert page_text(view) == "Page 3"
    assert buttons(view) == [(PREV, None, False), (None, "3/3", True), (NEXT, None, True)]

    await press(view, PREV)
    assert page_text(view) == "Page 2"
    assert buttons(view) == [(PREV, None, False), (None, "2/3", True), (NEXT, None, False)]


async def test_multi_item_pages():
    """Each page shows all its items, then the controls."""
    pages = [
        [TextDisplay("Title 1"), Container(TextDisplay("Body 1"))],
        [TextDisplay("Title 2"), Container(TextDisplay("Body 2"))],
    ]
    view = PagedView(pages)
    await press(view, NEXT)
    components = view.to_components()

    assert [c["type"] for c in components] == [
        discord.ComponentType.text_display.value,
        discord.ComponentType.container.value,
        discord.ComponentType.action_row.value,
    ]
    assert components[0]["content"] == "Title 2"
    assert components[1]["components"][0]["content"] == "Body 2"


async def test_timeout_disables_only_controls():
    """Timing out disables the page controls but leaves page content usable."""
    link = Button(label="Link", url="https://example.com")
    pages = [[Section(TextDisplay(f"Page {i}"), accessory=link)] for i in range(2)]
    view = PagedView(pages)
    await view.on_timeout()

    assert not link.disabled
    assert buttons(view) == [(PREV, None, True), (None, "1/2", True), (NEXT, None, True)]


async def test_single_page_not_edited_on_timeout():
    """A single page has no controls, so timing out leaves it alone."""
    assert not make_view(1).disable_on_timeout
    assert make_view(2).disable_on_timeout


async def test_press_refreshes_parent():
    """Timeouts edit through the latest press, whose token is freshest."""
    view = make_view(2)
    interaction = make_interaction()
    await press(view, NEXT, interaction)

    assert view.parent is interaction


async def test_anyone_can_page_without_author():
    """Without an author, anyone may turn pages."""
    view = make_view(2)
    assert await view.interaction_check(make_interaction(5))


async def test_only_author_can_page():
    """With an author, only they may turn pages."""
    view = make_view(2, author=make_user(1))

    assert await view.interaction_check(make_interaction(1))
    assert not await view.interaction_check(make_interaction(2))
