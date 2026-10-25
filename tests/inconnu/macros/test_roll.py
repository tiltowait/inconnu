"""Tests for inconnu/macros/roll.py's hunt and Slake menu."""

import importlib
from collections.abc import Iterator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord
import pytest

from inconnu.macros.roll import _SlakeView, reroll_listener
from inconnu.roll import Roll
from models import VChar
from tests.characters import gen_char

# inconnu.macros exports a roll() function, which shadows the module
HUNT_LISTENERS: dict = getattr(importlib.import_module("inconnu.macros.roll"), "__HUNT_LISTENERS")


@pytest.fixture(autouse=True)
def clear_hunt_listeners() -> Iterator[None]:
    """Keep listeners from leaking between tests."""
    yield
    HUNT_LISTENERS.clear()


@pytest.fixture
def owner() -> discord.Member:
    """The hunter's player."""
    member = MagicMock(spec=discord.Member)
    member.display_name = "tiltowait"
    member.guild_avatar = "https://example.com/avatar.png"
    return member


@pytest.fixture
def character() -> VChar:
    """A Hungry vampire."""
    char = gen_char("vampire")
    char.hunger = 3
    return char


@pytest.fixture
def outcome() -> Roll:
    """A successful hunt roll."""
    roll = Roll(1, 0, 1)
    roll.normal.dice = [6]
    return roll


def make_interaction(owner: discord.Member) -> AsyncMock:
    """A button interaction from the owner."""
    inter = AsyncMock(spec=discord.Interaction)
    inter.user = owner
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


async def press(view: _SlakeView, inter: AsyncMock, slake_amount: int):
    """Press the menu button that slakes the given amount."""
    custom_id = next(cid for cid, amount in view.buttons.items() if amount == slake_amount)
    inter.data = {"custom_id": custom_id}
    await view.callback(inter)


@pytest.mark.parametrize("ephemeral", [False, True])
async def test_reroll_into_success_shows_menu(
    owner: discord.Member, character: VChar, outcome: Roll, ephemeral: bool
):
    """Rerolling a failed hunt into success shows the menu, privately for hidden rolls."""
    HUNT_LISTENERS[outcome.id] = None
    inter = make_interaction(owner)

    await reroll_listener(inter, character, outcome, ephemeral=ephemeral)

    inter.respond.assert_awaited_once_with(embed=ANY, view=ANY, ephemeral=ephemeral)
    assert outcome.id not in HUNT_LISTENERS


async def test_reroll_into_failure_deletes_menu(
    owner: discord.Member, character: VChar, outcome: Roll
):
    """Rerolling a successful hunt into failure deletes the unused menu."""
    menu = AsyncMock(spec=discord.WebhookMessage)
    HUNT_LISTENERS[outcome.id] = menu
    outcome.normal.dice = [2]

    await reroll_listener(make_interaction(owner), character, outcome)

    menu.delete.assert_awaited_once()
    assert outcome.id not in HUNT_LISTENERS


async def test_dont_slake_deletes_menu(owner: discord.Member, character: VChar, outcome: Roll):
    """Declining deletes the menu through the interaction, which works even
    when the menu is ephemeral."""
    HUNT_LISTENERS[outcome.id] = AsyncMock(spec=discord.WebhookMessage)
    view = _SlakeView(owner, character, outcome)
    inter = make_interaction(owner)

    await press(view, inter, _SlakeView.CANCEL_SLAKE)

    inter.response.defer.assert_awaited_once()
    inter.delete_original_response.assert_awaited_once()
    assert outcome.id not in HUNT_LISTENERS


@patch("inconnu.reference.resonance", new_callable=AsyncMock)
@patch("inconnu.misc.slake", new_callable=AsyncMock)
async def test_slaking_keeps_result_after_failed_reroll(
    mock_slake: AsyncMock,
    _: AsyncMock,
    owner: discord.Member,
    character: VChar,
    outcome: Roll,
):
    """Once they've slaked, rerolling the hunt into failure leaves the result alone."""
    menu = AsyncMock(spec=discord.WebhookMessage)
    HUNT_LISTENERS[outcome.id] = menu
    view = _SlakeView(owner, character, outcome)
    inter = make_interaction(owner)

    await press(view, inter, 1)
    outcome.normal.dice = [2]
    await reroll_listener(inter, character, outcome)

    mock_slake.assert_awaited_once_with(inter, character, 1, edit_message=True)
    menu.delete.assert_not_awaited()
