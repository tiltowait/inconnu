"""Tests for inconnu/experience/remove.py."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import inconnu.experience.remove as remove_module
from inconnu.experience.remove import _entry_scope, _ExperienceView
from models import VChar
from models.vchardocs import VCharExperienceEntry

type MockInteraction = MagicMock
type MockMember = MagicMock
type MockDisplay = AsyncMock


@pytest.fixture
def character() -> VChar:
    """A character with some XP."""
    char = VChar(
        guild=1,
        user=2,
        name="Nadea",
        splat="vampire",
        health="......",
        willpower="......",
        humanity=7,
        stains=0,
        potency=1,
    )
    char.experience.unspent = 10
    char.experience.lifetime = 20
    return char


@pytest.fixture
def interaction() -> MockInteraction:
    """A server member's button press."""
    inter = MagicMock(spec=discord.Interaction)
    inter.response = MagicMock(spec=discord.InteractionResponse)
    inter.response.edit_message = AsyncMock()
    inter.user = MagicMock(spec=discord.Member)
    return inter


@pytest.fixture
def mock_display() -> Iterator[MockDisplay]:
    """Patch the character display and its side effects."""
    with (
        patch.object(remove_module, "display", new_callable=AsyncMock) as display,
        patch.object(remove_module, "get_message", new_callable=AsyncMock),
        patch.object(remove_module.services, "post_update", new_callable=AsyncMock),
        patch.object(VChar, "save_changes", new_callable=AsyncMock),
    ):
        yield display


def _press_view(character: VChar, event: str, amount: int) -> _ExperienceView:
    """Create the view for deleting a log entry."""
    entry = VCharExperienceEntry(event=event, amount=amount, reason="Test", admin=123)
    player: MockMember = MagicMock(spec=discord.Member)
    return _ExperienceView(character, player, entry)


async def test_apply_xp_unspent(
    character: VChar, interaction: MockInteraction, mock_display: MockDisplay
):
    """Deleting an unspent award removes it from unspent XP only."""
    view = _press_view(character, "award_unspent", 3)
    await view.apply_xp(interaction)

    assert character.experience.unspent == 7
    assert character.experience.lifetime == 20
    assert mock_display.await_args is not None
    assert mock_display.await_args.kwargs["message"] == "* `-3` unspent XP."


async def test_apply_xp_lifetime(
    character: VChar, interaction: MockInteraction, mock_display: MockDisplay
):
    """Reverting a lifetime deduction raises both lifetime and unspent XP."""
    view = _press_view(character, "deduct_lifetime", -4)
    await view.apply_xp(interaction)

    assert character.experience.unspent == 14
    assert character.experience.lifetime == 24
    assert mock_display.await_args is not None
    assert mock_display.await_args.kwargs["message"] == ("* `+4` unspent XP.\n* `+4` lifetime XP.")


async def test_apply_xp_lifetime_floor(
    character: VChar, interaction: MockInteraction, mock_display: MockDisplay
):
    """Lifetime XP can't go below zero, and the message shows what changed."""
    view = _press_view(character, "award_lifetime", 25)
    await view.apply_xp(interaction)

    assert character.experience.lifetime == 0
    assert character.experience.unspent == -10
    assert mock_display.await_args is not None
    assert mock_display.await_args.kwargs["message"] == (
        "* `-20` unspent XP.\n* `-20` lifetime XP."
    )


# Test basic functionality


def test_entry_scope_unspent():
    """Test extracting 'unspent' scope from event."""
    entry = VCharExperienceEntry(event="xp_unspent", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Unspent"


def test_entry_scope_lifetime():
    """Test extracting 'lifetime' scope from event."""
    entry = VCharExperienceEntry(event="xp_lifetime", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Lifetime"


def test_entry_scope_total():
    """Test extracting 'total' scope from event."""
    entry = VCharExperienceEntry(event="xp_total", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Total"


# Test capitalization


def test_entry_scope_capitalizes():
    """Test that the scope is capitalized."""
    entry = VCharExperienceEntry(event="xp_something", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Something"
    assert result[0].isupper()


def test_entry_scope_capitalizes_lowercase_input():
    """Test capitalization even if input is lowercase."""
    entry = VCharExperienceEntry(event="prefix_lowercase", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Lowercase"


# Test with different prefixes


def test_entry_scope_different_prefix():
    """Test that it works with any prefix before underscore."""
    entry = VCharExperienceEntry(event="prefix_scope", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Scope"


def test_entry_scope_long_prefix():
    """Test with longer prefix."""
    entry = VCharExperienceEntry(event="very_long_prefix_value", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Value"


# Test edge cases


def test_entry_scope_single_word():
    """Test with single word (no underscore)."""
    entry = VCharExperienceEntry(event="single", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Single"


def test_entry_scope_multiple_underscores():
    """Test with multiple underscores - should take last segment."""
    entry = VCharExperienceEntry(event="one_two_three_four", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Four"


def test_entry_scope_empty_after_underscore():
    """Test with empty string after final underscore."""
    entry = VCharExperienceEntry(event="prefix_", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == ""


def test_entry_scope_uppercase_input():
    """Test that uppercase input is capitalized (first upper, rest as-is)."""
    entry = VCharExperienceEntry(event="prefix_UPPERCASE", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    # capitalize() makes first char upper, rest lower
    assert result == "Uppercase"


def test_entry_scope_mixed_case_input():
    """Test mixed case input."""
    entry = VCharExperienceEntry(event="prefix_MiXeD", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Mixed"


# Test with realistic data


def test_entry_scope_realistic_xp_unspent():
    """Test with realistic XP unspent event."""
    entry = VCharExperienceEntry(event="award_unspent", amount=5, reason="Session play", admin=123)
    result = _entry_scope(entry)
    assert result == "Unspent"


def test_entry_scope_realistic_xp_lifetime():
    """Test with realistic XP lifetime event."""
    entry = VCharExperienceEntry(event="award_lifetime", amount=5, reason="Session play", admin=123)
    result = _entry_scope(entry)
    assert result == "Lifetime"


# Test that it only uses the 'event' key


def test_entry_scope_ignores_other_keys():
    """Test that only the 'event' key is used."""
    entry = VCharExperienceEntry(event="xp_unspent", amount=10, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Unspent"


# Test with numbers in scope


def test_entry_scope_with_numbers():
    """Test scope with numbers."""
    entry = VCharExperienceEntry(event="prefix_scope123", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "Scope123"


def test_entry_scope_numbers_only():
    """Test scope that's only numbers."""
    entry = VCharExperienceEntry(event="prefix_123", amount=5, reason="Test", admin=123)
    result = _entry_scope(entry)
    assert result == "123"


@pytest.mark.parametrize(
    "event,amount,label",
    [
        ("award_unspent", 3, "Remove 3 Unspent XP"),
        ("deduct_lifetime", -4, "Add 4 Lifetime XP"),
    ],
)
async def test_button_label(character: VChar, event: str, amount: int, label: str):
    """The button offers to reverse the deleted entry."""
    view = _press_view(character, event, amount)
    button = view.children[0]

    assert isinstance(button, discord.ui.Button)
    assert button.label == label


@pytest.mark.parametrize("storyteller", [True, False])
async def test_only_storytellers_press(
    character: VChar, interaction: MockInteraction, storyteller: bool
):
    """Only Storytellers can apply the reversal."""
    interaction.response.send_message = AsyncMock()
    view = _press_view(character, "award_unspent", 3)

    with patch.object(
        remove_module, "is_storyteller", new_callable=AsyncMock, return_value=storyteller
    ):
        assert await view.interaction_check(interaction) is storyteller

    assert interaction.response.send_message.await_count == (0 if storyteller else 1)


async def test_apply_xp_finishes(
    character: VChar, interaction: MockInteraction, mock_display: MockDisplay
):
    """Pressing removes the button, saves, reports the change, and ends the view."""
    view = _press_view(character, "award_unspent", 3)
    with (
        patch.object(VChar, "save_changes", new_callable=AsyncMock) as save,
        patch.object(remove_module.services, "post_update", new_callable=AsyncMock) as post,
    ):
        await view.apply_xp(interaction)

    interaction.response.edit_message.assert_awaited_once_with(view=None)
    save.assert_awaited_once()
    post.assert_awaited_once()
    assert view.is_finished()
