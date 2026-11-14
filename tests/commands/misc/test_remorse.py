"""Tests for inconnu/misc/remorse.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from ctx import AppCtx
from inconnu.misc.remorse import remorse
from models.vchar import VChar


@pytest.mark.parametrize("die,humanity,stains", [(6, 7, 0), (1, 6, 0)])
async def test_remorse_outcome(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    die: int,
    humanity: int,
    stains: int,
):
    """Passing keeps Humanity; failing costs a point. Either way, the Stains clear."""
    vamp.humanity = 7
    vamp.stains = 2

    with patch("inconnu.d10", return_value=die):
        await remorse(ctx, vamp)

    assert (vamp.humanity, vamp.stains) == (humanity, stains)
    assert vamp.log.remorse_checks == 1
    mock_char_save.assert_awaited_once()


async def test_remorse_saved_if_display_fails(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """The outcome is saved before responding, so a failed response can't
    lose it."""
    vamp.stains = 2
    mock_character_display.side_effect = discord.HTTPException(MagicMock(), "Failed")

    with patch("inconnu.d10", return_value=6), pytest.raises(discord.HTTPException):
        await remorse(ctx, vamp)

    mock_char_save.assert_awaited_once()
