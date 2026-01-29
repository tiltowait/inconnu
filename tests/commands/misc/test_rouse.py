"""Rouse check tests."""

from unittest.mock import AsyncMock, patch

import pytest

import errors
import inconnu
from ctx import AppCtx
from inconnu.misc.rouse import rouse
from models.vchar import VChar


async def test_mortal_rouse_fails(mortal: VChar, ctx: AppCtx):
    """Test that mortals cannot make rouse checks."""
    with pytest.raises(errors.CharacterError, match="is a mortal"):
        await rouse(ctx, mortal, 1, "Test", False)


async def test_ghoul_rouse_takes_damage(ghoul: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test that ghouls take aggravated damage instead of rouse check."""
    initial_agg = ghoul.aggravated_hp

    with patch("inconnu.character.display", new_callable=AsyncMock) as mock_display:
        await rouse(ctx, ghoul, 1, "Test", False)

        # Verify aggravated damage increased
        assert ghoul.aggravated_hp == initial_agg + 1
        mock_char_save.assert_awaited()

        # Verify display was called with correct parameters
        mock_display.assert_awaited_once()
        call_args = mock_display.await_args
        assert call_args is not None
        assert call_args.kwargs["title"] == "Ghoul Rouse Damage"
        assert "Aggravated damage" in call_args.kwargs["message"]


@pytest.mark.parametrize(
    "die_result,expected_hunger",
    [
        (6, 1),  # Success - hunger stays at 1
        (10, 1),  # Critical success - hunger stays at 1
        (5, 2),  # Failure - hunger increases to 2
        (1, 2),  # Critical failure - hunger increases to 2
    ],
)
async def test_vamp_single_rouse(
    die_result: int,
    expected_hunger: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test single rouse check with different die results."""
    assert vamp.hunger == 1

    with (
        patch("inconnu.d10", return_value=die_result),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False)

        assert vamp.hunger == expected_hunger
        mock_char_save.assert_awaited()

        # Verify display was called
        mock_display.assert_awaited_once()
        call_args = mock_display.await_args
        assert call_args is not None

        if die_result >= 6:
            assert "Success" in call_args.kwargs["title"]
        else:
            assert "Failure" in call_args.kwargs["title"]


@pytest.mark.parametrize(
    "die_results,expected_successes,expected_failures",
    [
        ([6, 7], 2, 0),  # 2 successes
        ([5, 4], 0, 2),  # 2 failures
        ([6, 4], 1, 1),  # 1 success, 1 failure
        ([10, 1, 8], 2, 1),  # 2 successes, 1 failure
    ],
)
async def test_vamp_multiple_rouse(
    die_results: list[int],
    expected_successes: int,
    expected_failures: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test multiple rouse checks."""
    initial_hunger = vamp.hunger
    count = len(die_results)

    # Create a mock that returns values in sequence
    die_mock = iter(die_results)

    with (
        patch("inconnu.d10", side_effect=lambda: next(die_mock)),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, count, "Test", False)

        expected_hunger = min(initial_hunger + expected_failures, 5)
        assert vamp.hunger == expected_hunger
        mock_char_save.assert_awaited()

        # Verify display title
        call_args = mock_display.await_args
        assert call_args is not None
        title = call_args.kwargs["title"]

        if expected_successes > 0 and expected_failures > 0:
            assert "success" in title.lower()
            assert "failure" in title.lower()
        elif expected_failures > 0:
            # Multiple failures use "failures" not "Failure"
            assert "failure" in title.lower()
        else:
            # Multiple successes use "successes" not "Success"
            assert "success" in title.lower()


async def test_vamp_rouse_with_reroll(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test rouse check with reroll on failures."""
    # First roll fails (4), reroll succeeds (7)
    die_results = iter([4, 7])

    with (
        patch("inconnu.d10", side_effect=lambda: next(die_results)),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", True)

        # Should succeed due to reroll, hunger stays at 1
        assert vamp.hunger == 1
        mock_char_save.assert_awaited()

        # Verify reroll is shown in footer
        call_args = mock_display.await_args
        assert call_args is not None
        footer = call_args.kwargs["footer"]
        assert "Re-rolling failures" in footer


async def test_vamp_rouse_reroll_both_fail(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test rouse check where both original and reroll fail."""
    # First roll fails (3), reroll also fails (4)
    die_results = iter([3, 4])

    with (
        patch("inconnu.d10", side_effect=lambda: next(die_results)),
        patch("inconnu.character.display", new_callable=AsyncMock),
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", True)

        # Should fail, hunger increases to 2
        assert vamp.hunger == 2
        mock_char_save.assert_awaited()


@pytest.mark.parametrize(
    "oblivion_values,die_result,expected_stains",
    [
        ([1, 10], 1, 1),  # Die shows 1, which is in oblivion list
        ([1, 10], 10, 1),  # Die shows 10, which is in oblivion list
        ([1, 10], 5, 0),  # Die shows 5, not in oblivion list
        ([], 1, 0),  # No oblivion values set
    ],
)
async def test_vamp_rouse_oblivion_stains_show(
    oblivion_values: list[int],
    die_result: int,
    expected_stains: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test rouse checks with oblivion stains (show mode)."""
    with (
        patch("inconnu.d10", return_value=die_result),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(
            inconnu.settings,
            "oblivion_stains",
            new_callable=AsyncMock,
            return_value=oblivion_values,
        ),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False, oblivion="show")

        mock_char_save.assert_awaited()

        # Verify stains message appears in footer if stains > 0
        call_args = mock_display.await_args
        assert call_args is not None
        footer = call_args.kwargs["footer"]

        if expected_stains > 0:
            assert "Oblivion" in footer
            assert "stain" in footer.lower()
        else:
            # Footer might not contain oblivion reference
            if footer:
                assert "Oblivion" not in footer


async def test_vamp_rouse_oblivion_stains_apply(
    vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock
):
    """Test rouse checks with oblivion stains in apply mode."""
    initial_stains = vamp.stains

    with (
        patch("inconnu.d10", return_value=1),  # Roll a 1
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(
            inconnu.settings,
            "oblivion_stains",
            new_callable=AsyncMock,
            return_value=[1, 10],  # 1 and 10 cause stains
        ),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False, oblivion="apply")

        # Stains should be applied to character
        assert vamp.stains == initial_stains + 1
        mock_char_save.assert_awaited()

        # Verify stains field is shown
        call_args = mock_display.await_args
        assert call_args is not None
        fields = call_args.kwargs["fields"]
        # Should have Hunger field and Humanity field (for stains)
        assert len(fields) == 2


async def test_vamp_rouse_multiple_oblivion_stains(
    vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock
):
    """Test multiple rouse checks with multiple oblivion stains."""
    die_results = iter([1, 10, 5])  # 1 and 10 cause stains, 5 doesn't

    with (
        patch("inconnu.d10", side_effect=lambda: next(die_results)),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(
            inconnu.settings,
            "oblivion_stains",
            new_callable=AsyncMock,
            return_value=[1, 10],
        ),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 3, "Test", False, oblivion="show")

        mock_char_save.assert_awaited()

        # Verify stains message
        call_args = mock_display.await_args
        assert call_args is not None
        footer = call_args.kwargs["footer"]
        assert "2 stains" in footer


async def test_vamp_rouse_at_hunger_5(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test rouse check when already at hunger 5 (frenzy condition)."""
    vamp.hunger = 5

    with (
        patch("inconnu.d10", return_value=6),  # Success
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False)

        # Hunger stays at 5
        assert vamp.hunger == 5
        mock_char_save.assert_awaited()

        # Verify frenzy warning appears
        call_args = mock_display.await_args
        assert call_args is not None
        custom = call_args.kwargs.get("custom")
        assert custom is not None
        assert "frenzy" in str(custom).lower()


async def test_vamp_rouse_hunger_5_failure(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test rouse check failure at hunger 5 (torpor/frenzy condition)."""
    vamp.hunger = 5

    with (
        patch("inconnu.d10", return_value=3),  # Failure
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False)

        # Hunger stays at 5
        assert vamp.hunger == 5
        mock_char_save.assert_awaited()

        # Verify torpor/frenzy warning appears
        call_args = mock_display.await_args
        assert call_args is not None
        custom = call_args.kwargs.get("custom")
        assert custom is not None
        custom_text = str(custom).lower()
        assert "torpor" in custom_text
        assert "frenzy" in custom_text


async def test_thin_blood_rouse(thin_blood: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test that thin-bloods can make rouse checks."""
    assert thin_blood.hunger == 1

    with (
        patch("inconnu.d10", return_value=3),  # Failure
        patch("inconnu.character.display", new_callable=AsyncMock),
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, thin_blood, 1, "Test", False)

        # Thin-bloods increase hunger like vampires
        assert thin_blood.hunger == 2
        mock_char_save.assert_awaited()


async def test_vamp_rouse_purpose_in_footer(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test that purpose appears in the footer."""
    purpose = "Activating Discipline"

    with (
        patch("inconnu.d10", return_value=6),
        patch("inconnu.character.display", new_callable=AsyncMock) as mock_display,
        patch("services.character_update", new_callable=AsyncMock),
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, purpose, False)

        mock_char_save.assert_awaited()

        call_args = mock_display.await_args
        assert call_args is not None
        footer = call_args.kwargs["footer"]
        assert purpose in footer


async def test_vamp_rouse_high_hunger_color(vamp: VChar, ctx: AppCtx, mock_char_save: AsyncMock):
    """Test that high hunger (>= 4) uses special color in report."""
    vamp.hunger = 3  # Will become 4 after failure

    with (
        patch("inconnu.d10", return_value=3),  # Failure
        patch("inconnu.character.display", new_callable=AsyncMock),
        patch("services.character_update", new_callable=AsyncMock) as mock_report,
        patch.object(inconnu.settings, "oblivion_stains", new_callable=AsyncMock, return_value=[]),
        patch("inconnu.get_message", new_callable=AsyncMock),
    ):
        await rouse(ctx, vamp, 1, "Test", False)

        assert vamp.hunger == 4
        mock_char_save.assert_awaited()

        # Verify report_update was called with danger color
        call_args = mock_report.await_args
        assert call_args is not None
        color = call_args.kwargs.get("color")
        assert color is not None
        assert color == inconnu.constants.ROUSE_FAIL_COLOR
