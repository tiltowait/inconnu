"""Tests for ui/views/ephemeralsafeview.py."""

from unittest.mock import AsyncMock

import discord
import pytest

from ui.views import EphemeralSafeView

type MockMessage = AsyncMock


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
    view = EphemeralSafeView()
    handle = AsyncMock(spec=original)
    view.message = handle

    view.message = make_message(ephemeral=True)

    assert view.message is handle


async def test_press_replaces_public_handle():
    """On a public message, a press's plain Message is used."""
    view = EphemeralSafeView()
    view.message = make_message(ephemeral=False, spec=discord.InteractionMessage)
    pressed = make_message(ephemeral=False)

    view.message = pressed

    assert view.message is pressed


async def test_first_handle_set():
    """With no handle yet, even an ephemeral plain Message is used."""
    view = EphemeralSafeView()
    message = make_message(ephemeral=True)

    view.message = message

    assert view.message is message


async def test_new_interaction_handle_replaces():
    """An interaction-backed handle replaces an earlier one."""
    view = EphemeralSafeView()
    view.message = make_message(ephemeral=True, spec=discord.InteractionMessage)
    followup = make_message(ephemeral=True, spec=discord.WebhookMessage)

    view.message = followup

    assert view.message is followup
