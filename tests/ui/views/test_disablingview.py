"""Tests for ui/views/disablingview.py."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ui import Button, Select

from ui.views import DisablingView

type MockInteraction = MagicMock
type MockMessage = AsyncMock

LINK = "https://example.com"


def make_view(*, remove_on_timeout: bool = False) -> tuple[DisablingView, Button, Select, Button]:
    """A view whose items, including a link button, are added after __init__."""
    view = DisablingView(remove_on_timeout=remove_on_timeout)
    button = Button(label="Press")
    select = Select(options=[discord.SelectOption(label="Pick")])
    link = Button(label="Docs", url=LINK)
    for item in (button, select, link):
        view.add_item(item)
    return view, button, select, link


def make_interaction() -> MockInteraction:
    """A component interaction."""
    inter = MagicMock(spec=discord.Interaction)
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


async def test_disable_items():
    """Items added after __init__ are disabled; link buttons aren't."""
    view, button, select, link = make_view()
    inter = make_interaction()

    await view.disable_items(inter)

    assert button.disabled and select.disabled
    assert not link.disabled
    inter.response.edit_message.assert_awaited_once_with(view=view)
    assert view.is_finished()


async def test_timeout_after_disable_items():
    """The items stay filterable after disable_items() has used them."""
    view, button, select, _ = make_view()
    await view.disable_items(make_interaction())
    button.disabled = select.disabled = False
    view.message = AsyncMock(spec=discord.Message)

    await view.on_timeout()

    assert button.disabled and select.disabled


async def test_timeout_removes_items():
    """With remove_on_timeout, only the link button remains."""
    view, _, _, link = make_view(remove_on_timeout=True)
    message: MockMessage = AsyncMock(spec=discord.Message)
    view.message = message

    await view.on_timeout()

    assert view.children == [link]
    message.edit.assert_awaited_once_with(view=view)


async def test_timeout_edits_through_interaction():
    """An interaction as the message is edited through its original response."""
    view, button, _, _ = make_view()
    inter = make_interaction()
    view.message = inter

    await view.on_timeout()

    assert button.disabled
    inter.edit_original_response.assert_awaited_once_with(view=view)


async def test_timeout_without_message():
    """Without a message, nothing is changed."""
    view, button, _, _ = make_view()

    await view.on_timeout()

    assert not button.disabled


async def test_timeout_deleted_message():
    """A deleted message is ignored."""
    view, _, _, _ = make_view()
    message: MockMessage = AsyncMock(spec=discord.Message)
    message.edit.side_effect = discord.NotFound(MagicMock(status=404), "Unknown Message")
    view.message = message

    await view.on_timeout()


def make_message(*, ephemeral: bool, spec: type[discord.Message] = discord.Message) -> MockMessage:
    """A message of the given type, ephemeral or not."""
    message = AsyncMock(spec=spec)
    message.flags = discord.MessageFlags(ephemeral=ephemeral)
    return message


@pytest.mark.parametrize(
    "original",
    [discord.InteractionMessage, discord.WebhookMessage, discord.Interaction],
)
async def test_press_keeps_ephemeral_handle(original: type):
    """A press's plain Message doesn't replace a handle that can edit an
    ephemeral message."""
    view = DisablingView()
    handle = AsyncMock(spec=original)
    view.message = handle

    view.message = make_message(ephemeral=True)

    assert view.message is handle


async def test_press_replaces_public_handle():
    """On a public message, a press's plain Message is used."""
    view = DisablingView()
    view.message = make_message(ephemeral=False, spec=discord.InteractionMessage)
    pressed = make_message(ephemeral=False)

    view.message = pressed

    assert view.message is pressed


async def test_first_handle_set():
    """With no handle yet, even an ephemeral plain Message is used."""
    view = DisablingView()
    message = make_message(ephemeral=True)

    view.message = message

    assert view.message is message


async def test_new_interaction_handle_replaces():
    """An interaction-backed handle replaces an earlier one."""
    view = DisablingView()
    view.message = make_message(ephemeral=True, spec=discord.InteractionMessage)
    followup = make_message(ephemeral=True, spec=discord.WebhookMessage)

    view.message = followup

    assert view.message is followup
