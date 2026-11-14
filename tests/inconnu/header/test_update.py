"""Tests for inconnu.header.update."""

from collections.abc import Iterator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import inconnu
from ctx import AppCtx
from inconnu.header.update import _RPHeader, update_header
from models import VChar
from tests.characters import gen_char

type MockInteraction = MagicMock


@pytest.fixture
def vampire() -> VChar:
    """A vampire who can Blush."""
    return gen_char("vampire")


@pytest.fixture
def interaction() -> MockInteraction:
    """A modal submission."""
    inter = MagicMock(spec=discord.Interaction)
    inter.data = {}
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


@pytest.fixture
def mock_save() -> Iterator[AsyncMock]:
    """Patch saving the character."""
    with patch.object(VChar, "save_changes", new_callable=AsyncMock) as mock:
        yield mock


def label_item(modal: _RPHeader, index: int) -> Any:
    """The input inside the modal's given Label."""
    return cast(discord.ui.Label, modal.children[index]).item


def blush_options(character: VChar) -> list[str]:
    """The Blush select's option values."""
    modal = _RPHeader(character, title="Header")
    return [option.value for option in label_item(modal, 1).options]


async def submit(
    character: VChar,
    interaction: MockInteraction,
    location="The Rack",
    blush="1",
    merits="",
    flaws="",
    temp="",
):
    """Fill out the modal the way Discord does, then submit it."""
    modal = _RPHeader(character, title="Header")
    components = [
        {"component": {"value": location}},
        {"component": {"values": [blush]}},
        {"component": {"value": merits}},
        {"component": {"value": flaws}},
        {"component": {"value": temp}},
    ]
    modal._refresh(interaction, components)  # pyright: ignore[reportArgumentType]
    await modal.callback(interaction)


async def test_update_header_sends_modal(vampire: VChar):
    """The command opens a modal titled for the character."""
    ctx = AsyncMock(spec=AppCtx)
    ctx.send_modal = AsyncMock(spec=discord.InteractionResponse.send_modal)

    await update_header(ctx, vampire)

    ctx.send_modal.assert_awaited_once()
    modal = ctx.send_modal.await_args.args[0]
    assert isinstance(modal, _RPHeader)
    assert modal.title == f"RP Header: {vampire.name}"


async def test_update_header_truncates_title(vampire: VChar):
    """Discord limits modal titles to 45 characters."""
    vampire.name = "N" * 40
    ctx = AsyncMock(spec=AppCtx)
    ctx.send_modal = AsyncMock(spec=discord.InteractionResponse.send_modal)

    await update_header(ctx, vampire)

    assert len(ctx.send_modal.await_args.args[0].title) == 45


async def test_inputs_show_current_header(vampire: VChar):
    """The modal opens with the character's current header."""
    vampire.header.location = "The Rack"
    vampire.header.merits = "Beautiful"
    vampire.header.flaws = "Stench"
    vampire.header.temp = "Obfuscated"

    modal = _RPHeader(vampire, title="Header")

    assert label_item(modal, 0).value == "The Rack"
    assert label_item(modal, 2).value == "Beautiful"
    assert label_item(modal, 3).value == "Stench"
    assert label_item(modal, 4).value == "Obfuscated"


async def test_location_length_leaves_room_for_title(vampire: VChar):
    """The location can't push the header's title past 256 characters."""
    title = inconnu.header.header_title(vampire.name, "Not Blushed", "")

    modal = _RPHeader(vampire, title="Header")

    assert label_item(modal, 0).max_length == 256 - len(title)


async def test_vampire_blush_options(vampire: VChar):
    """Vampires who can Blush choose On or Off."""
    assert blush_options(vampire) == ["1", "0"]


@pytest.mark.parametrize("splat", ["mortal", "ghoul", "thin-blood"])
async def test_non_vampire_blush_options(splat: str):
    """Characters who don't Blush only get N/A."""
    assert blush_options(gen_char(splat)) == ["-1"]


async def test_high_humanity_blush_options(vampire: VChar):
    """Vampires at Humanity 9+ don't need to Blush."""
    vampire.humanity = 9
    assert blush_options(vampire) == ["-1"]


@pytest.mark.parametrize(
    "blush,expected",
    [("1", 1), ("0", 0), ("-1", -1)],
)
async def test_callback_sets_blush(
    blush: str,
    expected: int,
    vampire: VChar,
    interaction: MockInteraction,
    mock_save: AsyncMock,
):
    """The Blush select's value becomes the header's integer Blush."""
    await submit(vampire, interaction, blush=blush)

    assert vampire.header.blush == expected


async def test_callback_sets_fields(
    vampire: VChar, interaction: MockInteraction, mock_save: AsyncMock
):
    """Each input lands in its own header field."""
    await submit(
        vampire,
        interaction,
        location="The Rack",
        merits="Beautiful",
        flaws="Stench",
        temp="Obfuscated",
    )

    assert vampire.header.location == "The Rack"
    assert vampire.header.merits == "Beautiful"
    assert vampire.header.flaws == "Stench"
    assert vampire.header.temp == "Obfuscated"


async def test_callback_cleans_text(
    vampire: VChar, interaction: MockInteraction, mock_save: AsyncMock
):
    """Extra spaces are removed, as are bullets from the location."""
    await submit(
        vampire,
        interaction,
        location="  The • Rack  ",
        merits="  Very   Beautiful ",
        flaws=" Foul   Stench ",
        temp=" Fully   Obfuscated ",
    )

    assert vampire.header.location == "The Rack"
    assert vampire.header.merits == "Very Beautiful"
    assert vampire.header.flaws == "Foul Stench"
    assert vampire.header.temp == "Fully Obfuscated"


async def test_callback_clears_optional_fields(
    vampire: VChar, interaction: MockInteraction, mock_save: AsyncMock
):
    """Emptied inputs clear their fields."""
    vampire.header.merits = "Beautiful"

    await submit(vampire, interaction, merits="")

    assert vampire.header.merits == ""


@pytest.mark.parametrize("location", ["•", " • • "])
async def test_callback_rejects_blank_location(
    location: str, vampire: VChar, interaction: MockInteraction, mock_save: AsyncMock
):
    """A location of only bullets gets no response, which keeps the modal open."""
    vampire.header.location = "The Rack"

    await submit(vampire, interaction, location=location, merits="Beautiful")

    interaction.response.send_message.assert_not_awaited()
    mock_save.assert_not_awaited()
    assert vampire.header.location == "The Rack"
    assert vampire.header.merits != "Beautiful"


async def test_callback_saves_and_responds(
    vampire: VChar, interaction: MockInteraction, mock_save: AsyncMock
):
    """The character is saved and the user privately told."""
    await submit(vampire, interaction)

    mock_save.assert_awaited_once()
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.await_args
    assert vampire.name in args[0]
    assert kwargs["ephemeral"] is True
