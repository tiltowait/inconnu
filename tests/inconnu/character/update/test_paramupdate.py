"""Tests for non-trait parameter updates."""

from unittest.mock import AsyncMock, patch

import pytest

import services
from inconnu.character.update.paramupdate import update_name
from models import VChar
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


async def test_update_name_same_name():
    """Renaming a character to its current name is rejected."""
    char = make_char("Nadea", user=1)

    with patch_char_mgr(char):
        with pytest.raises(ValueError, match="already this character's name"):
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

    with patch_char_mgr(spc):
        with pytest.raises(ValueError, match="already this character's name"):
            await update_name(spc, "Nadea")


async def test_update_name_spc_duplicate():
    """Regression: renaming an SPC to another SPC's name is rejected."""
    spc = make_char("Nadea", user=VChar.SPC_OWNER)
    other = make_char("Theron", user=VChar.SPC_OWNER)

    with patch_char_mgr(spc, other):
        with pytest.raises(ValueError, match="already have a character"):
            await update_name(spc, "Theron")
