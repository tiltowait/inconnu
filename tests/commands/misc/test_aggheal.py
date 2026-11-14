"""Aggravated healing tests."""

from unittest.mock import AsyncMock, patch

import pytest

from ctx import AppCtx
from inconnu.misc.aggheal import aggheal
from models.vchar import VChar


@pytest.mark.parametrize(
    "dice,hunger,successes,failures,gained",
    [
        ([6, 7, 8], 1, 3, 0, 0),  # All successes
        ([1, 6, 2], 1, 1, 2, 2),  # Two failures
        ([1, 2, 3], 4, 0, 3, 1),  # Hunger caps at 5 (torpor)
    ],
)
async def test_aggheal_logs_rouse(
    dice: list[int],
    hunger: int,
    successes: int,
    failures: int,
    gained: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that Aggravated healing logs three Rouse checks and the Hunger gained."""
    vamp.hunger = hunger
    vamp.set_aggravated_hp(1)
    rolls = iter(dice)

    with patch("inconnu.d10", side_effect=lambda: next(rolls)):
        await aggheal(ctx, vamp)

    assert vamp.aggravated_hp == 0
    assert vamp.hunger == hunger + gained
    assert vamp.log.rouse_checks == 3
    assert vamp.log.rouse_successes == successes
    assert vamp.log.rouse_failures == failures
    assert vamp.log.hunger_gained == gained
    mock_char_save.assert_awaited()
