"""Mend Superficial Damage tests."""

from unittest.mock import AsyncMock, patch

import pytest

import errors
import ui
from constants import ROUSE_FAIL_COLOR, Damage
from ctx import AppCtx
from inconnu.misc.mend import mend
from models.vchar import VChar


async def test_no_superficial_damage_fails(vamp: VChar, ctx: AppCtx):
    """Test that mending with no superficial damage fails."""
    vamp.health = "..........."  # All healthy

    with pytest.raises(errors.CharacterError, match="has no damage to mend"):
        await mend(ctx, vamp)


@pytest.mark.parametrize(
    "die_result,expected_hunger",
    [
        (6, 1),  # Rouse success - hunger stays at 1
        (10, 1),  # Critical success - hunger stays at 1
        (5, 2),  # Rouse failure - hunger increases to 2
        (1, 2),  # Critical failure - hunger increases to 2
    ],
)
async def test_vamp_mend_rouse_check(
    die_result: int,
    expected_hunger: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test mending with different rouse check results."""
    vamp.hunger = 1
    vamp.health = "/......"  # 1 superficial, rest healthy

    with patch("inconnu.d10", return_value=die_result):
        await mend(ctx, vamp)

    assert vamp.hunger == expected_hunger
    mock_char_save.assert_awaited()

    # Verify display was called
    mock_character_display.assert_awaited_once()
    call_args = mock_character_display.await_args
    assert call_args is not None

    # Check title includes rouse result
    title = call_args.kwargs["title"]
    if die_result >= 6:
        assert "Rouse Success" in title
    else:
        assert "Rouse Failure" in title

    # Verify report shows correct message
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]

    if die_result >= 6:
        assert "No Hunger gain" in message
    else:
        assert f"Gained `1` Hunger (now at `{expected_hunger}`)" in message


async def test_vamp_mend_at_hunger_5_rouse_failure(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test mending at hunger 5 with rouse failure triggers frenzy check."""
    vamp.hunger = 5
    vamp.health = "/......"  # 1 superficial

    with patch("inconnu.d10", return_value=3):  # Rouse failure
        await mend(ctx, vamp)

    assert vamp.hunger == 5  # Can't go above 5
    mock_char_save.assert_awaited()

    # Verify FrenzyView was created
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is not None
    assert isinstance(view, ui.views.FrenzyView)

    # Verify footer mentions frenzy
    footer = call_args.kwargs.get("footer")
    assert footer is not None
    assert "Hunger 5" in footer


async def test_vamp_mend_at_hunger_5_rouse_success(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test mending at hunger 5 with rouse success (no frenzy)."""
    vamp.hunger = 5
    vamp.health = "/......"  # 1 superficial

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    assert vamp.hunger == 5  # Stays at 5
    mock_char_save.assert_awaited()

    # Verify no FrenzyView
    call_args = mock_character_display.await_args
    assert call_args is not None
    view = call_args.kwargs.get("view")
    assert view is None


async def test_vamp_mend_partial_damage(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test mending when mend_amount < superficial damage."""
    vamp.health = "///......"  # 3 superficial damage
    initial_superficial = vamp.superficial_hp
    mend_amount = vamp.mend_amount

    # Ensure mend_amount is less than superficial
    assert mend_amount < initial_superficial

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    # Should mend exactly mend_amount
    assert vamp.superficial_hp == initial_superficial - mend_amount
    mock_char_save.assert_awaited()

    # Verify display shows correct mended amount
    call_args = mock_character_display.await_args
    assert call_args is not None
    title = call_args.kwargs["title"]
    assert f"Mended {mend_amount} damage" in title


async def test_vamp_mend_all_damage(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mending when mend_amount >= superficial damage."""
    vamp.health = "/......"

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    # Should mend all superficial damage
    assert vamp.superficial_hp == 0
    mock_char_save.assert_awaited()


async def test_vamp_mend_with_aggravated_damage(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mending superficial damage when aggravated damage is present."""
    vamp.health = "//x...."  # 2 superficial, 1 aggravated
    initial_aggravated = vamp.aggravated_hp

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    # Aggravated damage should remain unchanged
    assert vamp.aggravated_hp == initial_aggravated
    # Superficial should be reduced
    assert vamp.superficial_hp < 2
    mock_char_save.assert_awaited()


async def test_vamp_mend_health_track_correct(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that health track is correctly updated after mending."""
    vamp.health = "//x...."  # 2 superficial, 1 aggravated, 4 healthy
    mend_amount = vamp.mend_amount

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    # Health should be: (healthy + mended) + remaining_superficial + aggravated
    expected_superficial = max(0, 2 - mend_amount)
    expected_aggravated = 1
    expected_healthy = 7 - expected_superficial - expected_aggravated

    # Count damage types in health track
    health = vamp.health
    assert health.count(Damage.SUPERFICIAL) == expected_superficial
    assert health.count(Damage.AGGRAVATED) == expected_aggravated
    assert health.count(Damage.NONE) == expected_healthy


async def test_vamp_mend_fields_include_health_and_hunger(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that display fields include both Health and Hunger for vampires."""
    vamp.health = "/......"  # 1 superficial

    with patch("inconnu.d10", return_value=7):
        await mend(ctx, vamp)

    call_args = mock_character_display.await_args
    assert call_args is not None
    fields = call_args.kwargs["fields"]

    # Should have Health and Hunger fields
    assert len(fields) == 2
    field_names = [f[0] for f in fields]
    assert "Health" in field_names
    assert "Hunger" in field_names


async def test_vamp_mend_rouse_failure_color(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that rouse failure uses danger color."""
    vamp.health = "/......"  # 1 superficial

    with patch("inconnu.d10", return_value=3):  # Rouse failure
        await mend(ctx, vamp)

    call_args = mock_character_display.await_args
    assert call_args is not None
    color = call_args.kwargs.get("color")
    assert color is not None
    assert color == ROUSE_FAIL_COLOR


async def test_vamp_mend_rouse_success_no_color(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
):
    """Test that rouse success has no special color."""
    vamp.health = "/......"  # 1 superficial

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    call_args = mock_character_display.await_args
    assert call_args is not None
    color = call_args.kwargs.get("color")
    assert color is None


async def test_thin_blood_mend(
    thin_blood: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that thin-bloods can mend damage."""
    thin_blood.health = "/......"  # 1 superficial
    initial_hunger = thin_blood.hunger

    with patch("inconnu.d10", return_value=3):  # Rouse failure
        await mend(ctx, thin_blood)

    # Should heal and potentially gain hunger
    assert thin_blood.superficial_hp < 1
    # Thin-bloods are vampires, so they do rouse checks
    assert thin_blood.hunger == initial_hunger + 1
    mock_char_save.assert_awaited()


async def test_vamp_mend_multiple_superficial(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_character_display: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Test mending with multiple superficial damage."""
    vamp.health = "/////"  # 5 superficial
    mend_amount = vamp.mend_amount

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await mend(ctx, vamp)

    # Should mend mend_amount worth
    assert vamp.superficial_hp == 5 - mend_amount
    mock_char_save.assert_awaited()

    # Verify report message
    report_args = mock_common_report.await_args
    assert report_args is not None
    message = report_args.kwargs["message"]
    assert f"Mended `{mend_amount}` Superficial Damage" in message
    assert f"`{vamp.superficial_hp}` remaining" in message
