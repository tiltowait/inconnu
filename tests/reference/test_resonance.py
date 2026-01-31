"""Tests for inconnu/reference/resonance.py."""

import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from inconnu.reference.resonance import (
    Dyscrasia,
    _display_embed,
    _get_temperament,
    get_dyscrasia,
    get_resonance,
    random_temperament,
    resonance,
)
from models import ResonanceMode

# Test _get_temperament


def test_get_temperament_negligible():
    """Test _get_temperament returns Negligible for dice 1-5."""
    for die_value in range(1, 6):
        with patch("inconnu.d10", return_value=die_value):
            result = _get_temperament()
            assert result == "Negligible"


def test_get_temperament_fleeting():
    """Test _get_temperament returns Fleeting for dice 6-8."""
    for die_value in range(6, 9):
        with patch("inconnu.d10", return_value=die_value):
            result = _get_temperament()
            assert result == "Fleeting"


def test_get_temperament_intense():
    """Test _get_temperament returns Intense for 9-10 followed by 1-8."""
    for first_die in [9, 10]:
        for second_die in range(1, 9):
            with patch("inconnu.d10", side_effect=[first_die, second_die]):
                result = _get_temperament()
                assert result == "Intense"


def test_get_temperament_acute():
    """Test _get_temperament returns Acute for 9-10 followed by 9-10."""
    for first_die in [9, 10]:
        for second_die in [9, 10]:
            with patch("inconnu.d10", side_effect=[first_die, second_die]):
                result = _get_temperament()
                assert result == "Acute"


# Test get_resonance


@pytest.mark.parametrize(
    "mode,die_value,expected_resonance",
    [
        # STANDARD mode (1-10 range)
        (ResonanceMode.STANDARD, 1, "Phlegmatic"),
        (ResonanceMode.STANDARD, 2, "Phlegmatic"),
        (ResonanceMode.STANDARD, 3, "Phlegmatic"),
        (ResonanceMode.STANDARD, 4, "Melancholy"),
        (ResonanceMode.STANDARD, 5, "Melancholy"),
        (ResonanceMode.STANDARD, 6, "Melancholy"),
        (ResonanceMode.STANDARD, 7, "Choleric"),
        (ResonanceMode.STANDARD, 8, "Choleric"),
        (ResonanceMode.STANDARD, 9, "Sanguine"),
        (ResonanceMode.STANDARD, 10, "Sanguine"),
        # ADD_EMPTY mode (1-12 range)
        (ResonanceMode.ADD_EMPTY, 1, "Phlegmatic"),
        (ResonanceMode.ADD_EMPTY, 3, "Phlegmatic"),
        (ResonanceMode.ADD_EMPTY, 4, "Melancholy"),
        (ResonanceMode.ADD_EMPTY, 6, "Melancholy"),
        (ResonanceMode.ADD_EMPTY, 7, "Choleric"),
        (ResonanceMode.ADD_EMPTY, 8, "Choleric"),
        (ResonanceMode.ADD_EMPTY, 9, "Sanguine"),
        (ResonanceMode.ADD_EMPTY, 10, "Sanguine"),
        (ResonanceMode.ADD_EMPTY, 11, "Empty"),
        (ResonanceMode.ADD_EMPTY, 12, "Empty"),
        # TATTERED_FACADE mode (same as STANDARD for die values)
        (ResonanceMode.TATTERED_FACADE, 1, "Phlegmatic"),
        (ResonanceMode.TATTERED_FACADE, 5, "Melancholy"),
        (ResonanceMode.TATTERED_FACADE, 7, "Choleric"),
        (ResonanceMode.TATTERED_FACADE, 9, "Sanguine"),
    ],
)
def test_get_resonance(mode, die_value, expected_resonance):
    """Test get_resonance returns correct resonance for each die value and mode."""
    with patch("inconnu.random", return_value=die_value):
        die, res = get_resonance(mode)
        assert die == die_value
        assert res == expected_resonance


def test_get_resonance_standard_mode_cap():
    """Test that STANDARD mode uses 1-10 range."""
    with patch("inconnu.random", return_value=5) as mock_random:
        get_resonance(ResonanceMode.STANDARD)
        mock_random.assert_called_once_with(10)


def test_get_resonance_add_empty_mode_cap():
    """Test that ADD_EMPTY mode uses 1-12 range."""
    with patch("inconnu.random", return_value=5) as mock_random:
        get_resonance(ResonanceMode.ADD_EMPTY)
        mock_random.assert_called_once_with(12)


# Test get_dyscrasia


def test_get_dyscrasia_returns_dyscrasia():
    """Test get_dyscrasia returns a Dyscrasia object."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()

    # Create a Dyscrasia-like object using the row_factory
    test_dyscrasia = Dyscrasia("Test Dyscrasia", "A test description", 123)
    mock_cursor.fetchone.return_value = test_dyscrasia
    mock_cursor.execute.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_cursor

    with patch("sqlite3.connect", return_value=mock_conn):
        result = get_dyscrasia("Choleric")

        assert result is not None
        assert result.name == "Test Dyscrasia"
        assert result.description == "A test description"
        assert result.page == 123

        # Verify database query was correct
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "SELECT name, description, page FROM dyscrasias" in call_args[0][0]
        assert "WHERE resonance=?" in call_args[0][0]
        assert call_args[0][1] == ("Choleric",)

        # Verify connection was closed
        mock_conn.close.assert_called_once()


def test_get_dyscrasia_returns_none_when_not_found():
    """Test get_dyscrasia returns None when no dyscrasia is found."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = None
    mock_cursor.execute.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_cursor

    with patch("sqlite3.connect", return_value=mock_conn):
        result = get_dyscrasia("NonexistentResonance")

        assert result is None
        mock_conn.close.assert_called_once()


# Test async functions


async def test_random_temperament():
    """Test random_temperament generates temperament and displays embed."""
    # Create mock context
    mock_ctx = AsyncMock()
    mock_ctx.guild.id = 12345
    mock_ctx.user.display_name = "TestUser"
    mock_ctx.user.id = 1

    # Mock the settings service
    with (
        patch("services.settings.resonance_mode", new_callable=AsyncMock) as mock_mode,
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
    ):
        mock_mode.return_value = ResonanceMode.STANDARD

        # Mock the temperament generation
        with patch("inconnu.d10", return_value=7):
            await random_temperament(mock_ctx, "Choleric")

            # Verify respond was called with an embed
            mock_ctx.respond.assert_called_once()
            call_kwargs = mock_ctx.respond.call_args[1]
            assert "embed" in call_kwargs

            embed = call_kwargs["embed"]
            assert isinstance(embed, discord.Embed)
            assert "Fleeting Choleric Resonance" in embed.title


async def test_random_temperament_negligible():
    """Test random_temperament with Negligible temperament (no resonance shown)."""
    mock_ctx = AsyncMock()
    mock_ctx.guild.id = 12345
    mock_ctx.user.display_name = "TestUser"
    mock_ctx.user.id = 1

    with (
        patch("services.settings.resonance_mode", new_callable=AsyncMock) as mock_mode,
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
    ):
        mock_mode.return_value = ResonanceMode.STANDARD

        # Mock negligible temperament
        with patch("inconnu.d10", return_value=3):
            await random_temperament(mock_ctx, "Choleric")

            mock_ctx.respond.assert_called_once()
            embed = mock_ctx.respond.call_args[1]["embed"]
            assert "Negligible Resonance" in embed.title
            assert "Choleric" not in embed.title


async def test_resonance_with_temperament():
    """Test resonance command generates both temperament and resonance."""
    mock_ctx = AsyncMock()
    mock_ctx.guild.id = 12345
    mock_ctx.user.display_name = "TestUser"
    mock_ctx.user.id = 1

    with (
        patch("services.settings.resonance_mode", new_callable=AsyncMock) as mock_mode,
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
    ):
        mock_mode.return_value = ResonanceMode.STANDARD

        # Mock fleeting temperament and choleric resonance
        with patch("inconnu.d10", return_value=7), patch("inconnu.random", return_value=7):
            await resonance(mock_ctx)

            mock_ctx.respond.assert_called_once()
            embed = mock_ctx.respond.call_args[1]["embed"]
            assert "Fleeting Choleric Resonance" in embed.title
            assert embed.footer.text == "Rolled 7 for the Resonance"


async def test_resonance_negligible():
    """Test resonance command with negligible temperament."""
    mock_ctx = AsyncMock()
    mock_ctx.guild.id = 12345
    mock_ctx.user.display_name = "TestUser"
    mock_ctx.user.id = 1

    with (
        patch("services.settings.resonance_mode", new_callable=AsyncMock) as mock_mode,
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
    ):
        mock_mode.return_value = ResonanceMode.STANDARD

        # Mock negligible temperament
        with patch("inconnu.d10", return_value=3):
            await resonance(mock_ctx)

            mock_ctx.respond.assert_called_once()
            embed = mock_ctx.respond.call_args[1]["embed"]
            assert "Negligible Resonance" in embed.title
            # Should not have footer with die roll
            assert embed.footer is None


async def test_display_embed_standard_mode():
    """Test _display_embed with STANDARD mode disciplines."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    # Mock get_avatar
    with patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"):
        await _display_embed(
            mock_ctx,
            temperament="Fleeting",
            res="Choleric",
            die=7,
            mode=ResonanceMode.STANDARD,
        )

        mock_ctx.respond.assert_called_once()
        embed = mock_ctx.respond.call_args[1]["embed"]

        assert embed.title == "Fleeting Choleric Resonance"
        assert len(embed.fields) == 2
        assert embed.fields[0].name == "Disciplines"
        assert embed.fields[0].value == "Celerity, Potence"
        assert embed.fields[1].name == "Emotions & Conditions"
        assert "Angry, violent" in embed.fields[1].value
        assert embed.footer.text == "Rolled 7 for the Resonance"


async def test_display_embed_tattered_facade_mode():
    """Test _display_embed with TATTERED_FACADE mode disciplines."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    with patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"):
        await _display_embed(
            mock_ctx,
            temperament="Intense",
            res="Sanguine",
            die=9,
            mode=ResonanceMode.TATTERED_FACADE,
        )

        embed = mock_ctx.respond.call_args[1]["embed"]

        assert embed.fields[0].value == "Blood Sorcery, Presence, Protean"


async def test_display_embed_acute_with_dyscrasia():
    """Test _display_embed shows dyscrasia field for Acute temperament."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    mock_dyscrasia = Dyscrasia("Test Dyscrasia", "Description", 42)

    with (
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
        patch("inconnu.reference.resonance.get_dyscrasia", return_value=mock_dyscrasia),
    ):
        await _display_embed(
            mock_ctx,
            temperament="Acute",
            res="Melancholy",
            die=5,
            mode=ResonanceMode.STANDARD,
        )

        embed = mock_ctx.respond.call_args[1]["embed"]

        # Should have 3 fields: Disciplines, Emotions, and Dyscrasia
        assert len(embed.fields) == 3
        assert embed.fields[2].name == "Dyscrasia: Test Dyscrasia"
        assert "Description" in embed.fields[2].value
        assert "(p. 42)" in embed.fields[2].value
        assert embed.fields[2].inline is False


async def test_display_embed_acute_without_dyscrasia():
    """Test _display_embed when no dyscrasia is found."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    with (
        patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"),
        patch("inconnu.reference.resonance.get_dyscrasia", return_value=None),
    ):
        await _display_embed(
            mock_ctx,
            temperament="Acute",
            res="Phlegmatic",
            die=2,
            mode=ResonanceMode.STANDARD,
        )

        embed = mock_ctx.respond.call_args[1]["embed"]

        # Should only have 2 fields: Disciplines and Emotions (no Dyscrasia)
        assert len(embed.fields) == 2


async def test_display_embed_with_character_kwarg():
    """Test _display_embed uses character name from kwargs."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    with patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"):
        await _display_embed(
            mock_ctx,
            temperament="Fleeting",
            res="Sanguine",
            die=10,
            mode=ResonanceMode.STANDARD,
            character="Custom Character Name",
        )

        embed = mock_ctx.respond.call_args[1]["embed"]
        assert embed.author.name == "Custom Character Name"


async def test_display_embed_empty_resonance():
    """Test _display_embed with Empty resonance."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    with patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"):
        await _display_embed(
            mock_ctx,
            temperament="Fleeting",
            res="Empty",
            die=11,
            mode=ResonanceMode.ADD_EMPTY,
        )

        embed = mock_ctx.respond.call_args[1]["embed"]

        assert embed.title == "Fleeting Empty Resonance"
        assert embed.fields[0].value == "Oblivion"
        assert embed.fields[1].value == "No emotion"


async def test_display_embed_no_die():
    """Test _display_embed with no die value (None)."""
    mock_ctx = AsyncMock()
    mock_ctx.user.display_name = "TestUser"

    with patch("inconnu.reference.resonance.get_avatar", return_value="http://avatar.url"):
        await _display_embed(
            mock_ctx,
            temperament="Fleeting",
            res="Phlegmatic",
            die=None,
            mode=ResonanceMode.STANDARD,
        )

        embed = mock_ctx.respond.call_args[1]["embed"]

        # Should not have footer when die is None
        assert not hasattr(embed.footer, "text") or embed.footer.text == discord.Embed.Empty
