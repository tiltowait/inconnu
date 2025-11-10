"""Slake Hunger tests."""

from unittest.mock import AsyncMock

import pytest

import inconnu
from ctx import AppCtx
from inconnu.misc.slake import slake
from inconnu.models.vchar import VChar


async def test_mortal_slake_fails(mortal: VChar, ctx: AppCtx):
    """Test that mortals cannot slake hunger."""
    with pytest.raises(inconnu.errors.CharacterError, match="isn't a vampire"):
        await slake(ctx, mortal, 1)


async def test_ghoul_slake_fails(ghoul: VChar, ctx: AppCtx):
    """Test that ghouls cannot slake hunger."""
    with pytest.raises(inconnu.errors.CharacterError, match="isn't a vampire"):
        await slake(ctx, ghoul, 1)


async def test_vamp_hunger_zero_fails(vamp: VChar, ctx: AppCtx):
    """Test that vampires at hunger 0 cannot slake."""
    vamp.hunger = 0

    with pytest.raises(inconnu.errors.CharacterError, match="has no Hunger"):
        await slake(ctx, vamp, 1)


@pytest.mark.parametrize(
    "initial_hunger,amount,expected_hunger",
    [
        (1, 1, 0),  # Slake 1, hunger goes to 0
        (3, 1, 2),  # Slake 1, hunger goes to 2
        (5, 2, 3),  # Slake 2, hunger goes to 3
        (2, 5, 0),  # Slake more than current hunger, goes to 0
        (4, 4, 0),  # Slake exact amount
    ],
)
async def test_vamp_slake_basic(
    initial_hunger: int,
    amount: int,
    expected_hunger: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test basic hunger slaking."""
    vamp.hunger = initial_hunger
    expected_slaked = initial_hunger - expected_hunger

    await slake(ctx, vamp, amount)

    assert vamp.hunger == expected_hunger
    mock_char_save.assert_awaited()

    # Verify display was called with correct title
    mock_character_display.assert_awaited_once()
    call_args = mock_character_display.await_args
    assert call_args is not None
    assert f"Slaked {expected_slaked} Hunger" in call_args.kwargs["title"]

    # Verify fields include "New Hunger"
    fields = call_args.kwargs["fields"]
    assert len(fields) == 1
    assert "New Hunger" in fields[0][0]

    # Verify report update was called
    mock_common_report.assert_awaited_once()
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert f"slaked `{expected_slaked}` Hunger" in message
    assert f"now at `{expected_hunger}`" in message


@pytest.mark.parametrize("initial_hunger", [4, 5])
async def test_vamp_slake_high_hunger_frenzy_view(
    initial_hunger: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that slaking from high hunger (>= 4) shows FrenzyView."""
    vamp.hunger = initial_hunger

    await slake(ctx, vamp, 1)
    mock_char_save.assert_awaited()

    # Verify FrenzyView was created
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is not None
    assert isinstance(view, inconnu.views.FrenzyView)


@pytest.mark.parametrize("initial_hunger", [1, 2, 3])
async def test_vamp_slake_low_hunger_no_frenzy_view(
    initial_hunger: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that slaking from low hunger (< 4) has no FrenzyView."""
    vamp.hunger = initial_hunger

    await slake(ctx, vamp, 1)
    mock_char_save.assert_awaited()

    # Verify no FrenzyView was created
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is None


async def test_thin_blood_slake(
    thin_blood: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that thin-bloods can slake hunger."""
    thin_blood.hunger = 2

    await slake(ctx, thin_blood, 1)

    assert thin_blood.hunger == 1
    mock_char_save.assert_awaited()


async def test_vamp_slake_to_zero(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test slaking hunger to exactly 0."""
    vamp.hunger = 3

    await slake(ctx, vamp, 3)

    assert vamp.hunger == 0
    mock_char_save.assert_awaited()

    # Verify display shows slaked 3
    call_args = mock_character_display.await_args
    assert call_args is not None
    assert "Slaked 3 Hunger" in call_args.kwargs["title"]

    # Verify report shows now at 0
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert "now at `0`" in message


async def test_vamp_slake_more_than_current(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test slaking more hunger than current hunger."""
    vamp.hunger = 2

    await slake(ctx, vamp, 5)

    # Should only slake 2 (all current hunger)
    assert vamp.hunger == 0
    mock_char_save.assert_awaited()

    # Verify display shows slaked 2, not 5
    call_args = mock_character_display.await_args
    assert call_args is not None
    assert "Slaked 2 Hunger" in call_args.kwargs["title"]

    # Verify report shows slaked 2
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert "slaked `2` Hunger" in message


async def test_vamp_slake_from_hunger_5(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test slaking from maximum hunger (5)."""
    vamp.hunger = 5

    await slake(ctx, vamp, 1)

    assert vamp.hunger == 4
    mock_char_save.assert_awaited()

    # Should have FrenzyView (started at 5)
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is not None
    assert isinstance(view, inconnu.views.FrenzyView)


async def test_vamp_slake_across_frenzy_threshold(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test slaking from 4 to 2 (crossing frenzy threshold)."""
    vamp.hunger = 4

    await slake(ctx, vamp, 2)

    assert vamp.hunger == 2
    mock_char_save.assert_awaited()

    # Should have FrenzyView (started at 4)
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is not None
    assert isinstance(view, inconnu.views.FrenzyView)
