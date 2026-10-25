"""Tests for inconnu/character/display/display.py"""

from unittest.mock import AsyncMock, patch

import discord

from inconnu.character.display.display import display
from tests.characters import gen_char
from ui.views import DisablingView


def make_interaction() -> AsyncMock:
    """A button interaction."""
    inter = AsyncMock(spec=discord.Interaction)
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    return inter


async def test_display_edit_message():
    """Editing replaces the pressed button's message through the interaction,
    which also works for ephemeral messages, and removes its view."""
    inter = make_interaction()
    embed = discord.Embed(title="Slaked 1 Hunger")
    with patch(
        "inconnu.character.display.display.__get_embed", new_callable=AsyncMock, return_value=embed
    ):
        result = await display(inter, gen_char("vampire"), edit_message=True)

    inter.response.edit_message.assert_awaited_once_with(embed=embed, view=None)
    inter.respond.assert_not_awaited()
    assert result is inter


async def test_display_edit_message_disabling_view():
    """A DisablingView is attached, and it can later edit through the interaction."""
    inter = make_interaction()
    view = DisablingView()
    embed = discord.Embed(title="Slaked 1 Hunger")
    with patch(
        "inconnu.character.display.display.__get_embed", new_callable=AsyncMock, return_value=embed
    ):
        await display(inter, gen_char("vampire"), view=view, edit_message=True)

    inter.response.edit_message.assert_awaited_once_with(embed=embed, view=view)
    assert view.message is inter
