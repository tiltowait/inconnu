"""Tests for non-trait parameter updates."""

from unittest.mock import AsyncMock, patch

import pytest

import services
from inconnu.character.update.paramupdate import (
    update_health,
    update_name,
    update_stains,
    update_willpower,
)
from models import VChar
from models.vchar import Tracker
from tests.characters import gen_char


def make_char(name: str, user: int) -> VChar:
    """Generate a character with the given name and owner."""
    char = gen_char("vampire")
    char.guild = 1
    char.user = user
    char.name = name

    return char


def patch_char_mgr(*chars: VChar):
    """Patch the character manager's fetchall and sort_chars."""
    return patch.multiple(
        services.char_mgr,
        fetchall=AsyncMock(return_value=list(chars)),
        sort_chars=AsyncMock(),
    )


async def test_update_name():
    """A valid rename updates the raw name."""
    char = make_char("Nadea", user=1)

    with patch_char_mgr(char):
        message = await update_name(char, "Theron")

    assert char.raw_name == "Theron"
    assert "Theron" in message


async def test_update_name_collapses_whitespace():
    """The name is stored with its whitespace collapsed, as it was checked."""
    char = make_char("Nadea", user=1)

    with patch_char_mgr(char):
        message = await update_name(char, "  Theron\u00a0 Dusk\t")

    assert char.raw_name == "Theron Dusk"
    assert "`Theron Dusk`" in message


async def test_update_name_straightens_apostrophes():
    """Curly apostrophes, which phones type, are stored straight."""
    char = make_char("Nadea", user=1)

    with patch_char_mgr(char):
        await update_name(char, "O\u2019Brien")

    assert char.raw_name == "O'Brien"


@pytest.mark.parametrize("name", ["", "   "])
async def test_update_name_blank(name: str):
    """A blank name says so, rather than blaming its characters."""
    char = make_char("Nadea", user=1)

    with pytest.raises(ValueError, match="can't be blank"):
        await update_name(char, name)


async def test_update_name_too_long():
    """A name over the limit, once collapsed, reports the excess."""
    char = make_char("Nadea", user=1)

    with pytest.raises(ValueError, match="too long by 1 character\\."):
        await update_name(char, "a" * 31)


async def test_update_name_invalid_characters():
    """Invalid characters name everything a name may contain."""
    char = make_char("Nadea", user=1)

    with pytest.raises(ValueError, match="spaces, underscores, hyphens, and apostrophes"):
        await update_name(char, "Bad!")


async def test_update_name_same_name():
    """Renaming a character to its current name is rejected."""
    char = make_char("Nadea", user=1)

    with patch_char_mgr(char), pytest.raises(ValueError, match="already this character's name"):
        await update_name(char, "Nadea")


async def test_update_name_capitalization_fix():
    """A rename differing only in case skips the duplicate check."""
    char = make_char("nadea", user=1)

    with patch_char_mgr(char):
        await update_name(char, "Nadea")

    assert char.raw_name == "Nadea"


async def test_update_name_duplicate():
    """Renaming to another character's name is rejected."""
    char = make_char("Nadea", user=1)
    other = make_char("Theron", user=1)

    with patch_char_mgr(char, other):
        with pytest.raises(ValueError, match="already have a character"):
            await update_name(char, "theron")


async def test_update_name_spc_same_name():
    """Regression: renaming an SPC to its current name is rejected.

    The name property appends " (SPC)" to SPC names; comparing against it
    instead of raw_name let these renames through."""
    spc = make_char("Nadea", user=VChar.SPC_OWNER)
    assert spc.is_spc

    with patch_char_mgr(spc), pytest.raises(ValueError, match="already this character's name"):
        await update_name(spc, "Nadea")


async def test_update_name_spc_duplicate():
    """Regression: renaming an SPC to another SPC's name is rejected."""
    spc = make_char("Nadea", user=VChar.SPC_OWNER)
    other = make_char("Theron", user=VChar.SPC_OWNER)

    with patch_char_mgr(spc, other):
        with pytest.raises(ValueError, match="already have a character"):
            await update_name(spc, "Theron")


@pytest.mark.parametrize(
    "delta,expected_stains,expected_damage",
    [
        ("+2", 5, 2),  # Two Stains overflow Humanity 7
        ("6", 6, 3),  # Setting rather than adding
        ("-1", 2, 0),  # Removing Stains never deals damage
    ],
)
def test_update_stains_degeneration(delta: str, expected_stains: int, expected_damage: int):
    """Test that Stains set through updates trigger degeneration."""
    char = gen_char("vampire")
    char.humanity = 7
    char.stains = 3

    message = update_stains(char, delta)

    assert char.stains == expected_stains
    assert char.aggravated_wp == expected_damage
    if expected_damage:
        assert f"`+{expected_damage}` Aggravated Willpower damage" in message
    else:
        assert "Degeneration" not in message


@pytest.mark.parametrize(
    "tracker,rating,allowed",
    [
        (Tracker.HEALTH, 2, False),
        (Tracker.HEALTH, 3, True),
        (Tracker.HEALTH, 25, True),
        (Tracker.HEALTH, 26, False),
        (Tracker.WILLPOWER, 1, False),
        (Tracker.WILLPOWER, 2, True),  # Retainers can have 1 Resolve and Composure
        (Tracker.WILLPOWER, 25, True),
        (Tracker.WILLPOWER, 26, False),
    ],
)
def test_update_tracker_limits(tracker: Tracker, rating: int, allowed: bool):
    """Health and Willpower updates are limited to the tracker ranges."""
    char = gen_char("vampire")
    update = update_health if tracker == Tracker.HEALTH else update_willpower

    if allowed:
        update(char, str(rating))
        assert len(getattr(char, tracker)) == rating
    else:
        low, high = VChar.tracker_limits(tracker)
        with pytest.raises(ValueError, match=f"between {low} and {high}"):
            update(char, str(rating))
