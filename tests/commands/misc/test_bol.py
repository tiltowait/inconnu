"""Blush of Life tests."""

from unittest.mock import AsyncMock, patch

import pytest

import inconnu
from ctx import AppCtx
from inconnu.misc.bol import bol
from inconnu.models.vchar import VChar


@pytest.mark.parametrize("humanity", [7, 8, 9, 10])
async def test_vamp_bol(
    humanity: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
):
    """Test Blush of Life for vampires with varying Humanity levels."""
    assert vamp.hunger == 1
    vamp.humanity = humanity
    with patch("inconnu.misc.rouse", new_callable=AsyncMock) as mock_rouse:
        await bol(ctx, vamp, False)

        if humanity >= 9:
            assert mock_respond.await_args is not None
            args = mock_respond.await_args.args
            assert len(args) == 1
            assert "Blush of Life is unnecessary" in args[0]

            if humanity == 9:
                assert "only looks a little sick" in args[0]
            else:
                assert "looks hale and healthy" in args[0]

            mock_char_save.assert_not_awaited()
        else:
            mock_rouse.assert_awaited_once_with(
                ctx, vamp, 1, "Blush of Life", humanity == 8, oblivion=False
            )
            mock_char_save.assert_awaited()


@pytest.mark.parametrize("humanity", [6, 7, 8, 9, 10])
async def test_thin_blood_bol(
    humanity: int,
    thin_blood: VChar,
    ctx: AppCtx,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
):
    """Test Blush of Life for thin-bloods. They always have effective humanity >= 9."""
    thin_blood.humanity = humanity
    with patch("inconnu.misc.rouse", new_callable=AsyncMock) as mock_rouse:
        await bol(ctx, thin_blood, False)

        # Thin-bloods always have effective_humanity >= 9, so no rouse needed
        assert mock_respond.await_args is not None
        args = mock_respond.await_args.args
        assert len(args) == 1
        assert "Blush of Life is unnecessary" in args[0]

        if humanity >= 10:
            assert "looks hale and healthy" in args[0]
        else:
            assert "only looks a little sick" in args[0]

        mock_rouse.assert_not_awaited()
        mock_char_save.assert_not_awaited()


async def test_mortal_bol_fails(mortal: VChar, ctx: AppCtx):
    """Test that mortals cannot use Blush of Life."""
    with pytest.raises(inconnu.errors.CharacterError, match="isn't a vampire"):
        await bol(ctx, mortal, False)


async def test_ghoul_bol_fails(ghoul: VChar, ctx: AppCtx):
    """Test that ghouls cannot use Blush of Life."""
    with pytest.raises(inconnu.errors.CharacterError, match="isn't a vampire"):
        await bol(ctx, ghoul, False)


@pytest.mark.parametrize(
    "potency,expected_bane",
    [
        (1, 2),  # bane_severity = ceil(1/2) + 1 = 2
        (3, 3),  # bane_severity = ceil(3/2) + 1 = 3
    ],
)
async def test_vamp_ministry_bane(
    potency: int,
    expected_bane: int,
    vamp: VChar,
    ctx: AppCtx,
    mock_respond: AsyncMock,
    mock_char_save: AsyncMock,
):
    """Test Blush of Life with Ministry's Cold-Blooded bane."""
    vamp.humanity = 7
    vamp.potency = potency

    with patch("inconnu.misc.rouse", new_callable=AsyncMock) as mock_rouse:
        await bol(ctx, vamp, True)

        # Should use bane_severity for rouse count and update message
        mock_rouse.assert_awaited_once_with(
            ctx, vamp, expected_bane, "Blush of Life - Cold-Blooded bane", False, oblivion=False
        )
        mock_char_save.assert_awaited()
