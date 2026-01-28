"""Stain application tests."""

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from ctx import AppCtx
from inconnu.misc.stain import stain
from models.vchar import VChar


async def test_stain_delta_zero_fails(vamp: VChar, ctx: AppCtx):
    """Test that applying 0 stains raises an error."""
    # stain() doesn't use the filter, so we call it directly
    with patch("inconnu.embeds.error", new_callable=AsyncMock) as mock_error:
        await stain(ctx, vamp, 0, player=ctx.user)

        # Should call error embed
        mock_error.assert_awaited_once()
        call_args = mock_error.await_args
        assert call_args is not None
        assert "can't be zero" in str(call_args.args[1])


@pytest.mark.parametrize(
    "initial_stains,delta,expected_stains",
    [
        (0, 1, 1),  # Add 1 stain
        (0, 3, 3),  # Add 3 stains
        (2, 2, 4),  # Add 2 stains to existing 2 (at threshold, not over)
    ],
)
async def test_add_stains_no_degeneration(
    initial_stains: int,
    delta: int,
    expected_stains: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test adding stains without triggering degeneration.

    With humanity=6, degeneration threshold is 4 stains (10 - 6 = 4).
    Degeneration triggers when stains > 4.
    """
    vamp.humanity = 6
    vamp.stains = initial_stains

    await stain(ctx, vamp, delta, player=ctx.user)

    assert vamp.stains == expected_stains
    mock_char_save.assert_awaited()

    # Verify display was called
    call_args = mock_character_display.await_args
    assert call_args is not None

    title = call_args.args[2]
    assert "Added" in title
    assert f"{delta} Stain" in title

    # Should only have Humanity field (no degeneration)
    fields = call_args.kwargs["fields"]
    assert len(fields) == 1
    assert "Humanity" in fields[0][0]


@pytest.mark.parametrize(
    "initial_stains,delta,expected_stains",
    [
        (5, -1, 4),  # Remove 1 stain
        (5, -3, 2),  # Remove 3 stains
        (2, -2, 0),  # Remove all stains
        (10, -5, 5),  # Remove 5 stains
    ],
)
async def test_remove_stains(
    initial_stains: int,
    delta: int,
    expected_stains: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test removing stains."""
    vamp.stains = initial_stains

    await stain(ctx, vamp, delta, player=ctx.user)

    assert vamp.stains == expected_stains
    mock_char_save.assert_awaited()

    # Verify display title
    call_args = mock_character_display.await_args
    assert call_args is not None

    title = call_args.args[2]
    assert "Removed" in title
    assert f"{abs(delta)} Stain" in title


async def test_add_stains_clamp_to_10(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that adding stains clamps to maximum of 10."""
    vamp.humanity = 1  # Low humanity to avoid complications
    vamp.stains = 8

    await stain(ctx, vamp, 5, player=ctx.user)

    # Should clamp to 10, not go to 13
    assert vamp.stains == 10
    mock_char_save.assert_awaited()


async def test_remove_stains_clamp_to_0(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that removing stains clamps to minimum of 0."""
    vamp.stains = 2

    await stain(ctx, vamp, -5, player=ctx.user)

    # Should clamp to 0, not go negative
    assert vamp.stains == 0
    mock_char_save.assert_awaited()


async def test_add_stains_with_degeneration(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test adding stains that trigger degeneration."""
    vamp.willpower = "......."
    vamp.humanity = 6  # 10 - 6 = 4 stains before degeneration
    vamp.stains = 4  # At the threshold

    await stain(ctx, vamp, 2, player=ctx.user)  # Add 2 more, should trigger

    assert vamp.stains == 6
    mock_char_save.assert_awaited()

    # Verify display includes degeneration message
    call_args = mock_character_display.await_args
    assert call_args is not None

    message = call_args.kwargs.get("message")
    assert message is not None
    assert "Degeneration!" in message
    assert "Aggravated Willpower damage" in message

    # Should have both Humanity and Willpower fields
    fields = call_args.kwargs["fields"]
    assert len(fields) == 2
    field_names = [f[0] for f in fields]
    assert "Humanity" in field_names
    assert "Willpower" in field_names


async def test_degeneration_footer(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that degeneration footer appears when character.degeneration is true."""
    vamp.willpower = "......."
    vamp.humanity = 6
    vamp.stains = 4

    # Mock degeneration property to return True
    with patch.object(type(vamp), "degeneration", new_callable=PropertyMock) as mock_degen:
        mock_degen.return_value = True

        await stain(ctx, vamp, 2, player=ctx.user)

        call_args = mock_character_display.await_args
        assert call_args is not None

        footer = call_args.kwargs.get("footer")
        assert footer is not None
        assert "Degeneration!" in footer
        assert "-2 dice to all rolls" in footer


async def test_no_degeneration_footer_when_false(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that no footer appears when degeneration is false."""
    vamp.stains = 2

    # Mock degeneration property to return False
    with patch.object(type(vamp), "degeneration", new_callable=PropertyMock) as mock_degen:
        mock_degen.return_value = False

        await stain(ctx, vamp, 1, player=ctx.user)

        call_args = mock_character_display.await_args
        assert call_args is not None

        footer = call_args.kwargs.get("footer")
        assert footer is None


async def test_add_single_stain_singular(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test that adding 1 stain uses singular 'Stain' not 'Stains'."""
    vamp.stains = 0

    await stain(ctx, vamp, 1, player=ctx.user)
    mock_char_save.assert_awaited()

    # Check display title
    display_args = mock_character_display.await_args
    assert display_args is not None
    title = display_args.args[2]
    assert "1 Stain" in title

    # Check report message
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert "`1` Stain" in message
    assert "gained" in message


async def test_add_multiple_stains_plural(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test that adding multiple stains uses plural 'Stains'."""
    vamp.stains = 0

    await stain(ctx, vamp, 3, player=ctx.user)
    mock_char_save.assert_awaited()

    # Check display title
    display_args = mock_character_display.await_args
    assert display_args is not None
    title = display_args.args[2]
    assert "3 Stains" in title

    # Check report message
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert "`3` Stains" in message
    assert "gained" in message


async def test_remove_stains_report(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test that removing stains shows 'removed' in report."""
    vamp.stains = 5

    await stain(ctx, vamp, -2, player=ctx.user)
    mock_char_save.assert_awaited()

    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert "removed" in message
    assert "`2` Stains" in message


async def test_degeneration_overlap_calculation(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test degeneration overlap calculation for willpower damage."""
    vamp.willpower = "......."
    vamp.humanity = 7  # 10 - 7 = 3 stains before degeneration
    vamp.stains = 3  # At threshold
    initial_agg_wp = vamp.aggravated_wp

    # Adding 2 stains should cause 2 aggravated willpower damage
    await stain(ctx, vamp, 2, player=ctx.user)

    # Verify willpower damage was applied
    assert vamp.aggravated_wp == initial_agg_wp + 2
    mock_char_save.assert_awaited()


async def test_no_willpower_damage_when_removing_stains(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that removing stains doesn't add willpower damage."""
    vamp.willpower = "......."
    vamp.humanity = 6
    vamp.stains = 8  # In degeneration range
    initial_agg_wp = vamp.aggravated_wp

    await stain(ctx, vamp, -2, player=ctx.user)

    # Willpower should not change when removing stains
    assert vamp.aggravated_wp == initial_agg_wp
    mock_char_save.assert_awaited()

    # Should only have Humanity field, not Willpower
    call_args = mock_character_display.await_args
    assert call_args is not None
    fields = call_args.kwargs["fields"]
    assert len(fields) == 1
    assert "Humanity" in fields[0][0]


async def test_thin_blood_stains(
    thin_blood: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that thin-bloods can gain and remove stains."""
    thin_blood.stains = 0

    await stain(ctx, thin_blood, 3, player=ctx.user)

    assert thin_blood.stains == 3
    mock_char_save.assert_awaited()


async def test_stain_with_different_player(
    vamp: VChar,
    ctx: AppCtx,
    user: AsyncMock,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test stain command with player parameter."""
    vamp.stains = 0

    # Use a different player
    other_player = user

    await stain(ctx, vamp, 2, player=other_player)

    assert vamp.stains == 2
    mock_char_save.assert_awaited()

    # Verify owner was passed to display
    call_args = mock_character_display.await_args
    assert call_args is not None
    assert call_args.kwargs["owner"] == other_player
