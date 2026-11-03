"""Experience award/deduct tests."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import discord
import pytest

import inconnu.experience.award_deduct as award_deduct_module
from ctx import AppCtx
from inconnu.experience.award_deduct import award_or_deduct
from models.vchar import VChar


@pytest.fixture
def mock_error() -> Iterator[AsyncMock]:
    """Patch the error embed."""
    with patch.object(award_deduct_module.ui.embeds, "error", new_callable=AsyncMock) as mock:
        yield mock


def _permissions(unspent: bool, lifetime: bool):
    """Patch the server's XP permissions."""
    settings = award_deduct_module.services.settings
    return (
        patch.object(
            settings, "can_adjust_current_xp", new_callable=AsyncMock, return_value=unspent
        ),
        patch.object(
            settings, "can_adjust_lifetime_xp", new_callable=AsyncMock, return_value=lifetime
        ),
    )


@pytest.mark.parametrize(
    "scope,unspent_ok,lifetime_ok,allowed",
    [
        ("Unspent", True, False, True),
        ("Unspent", False, True, False),
        ("Lifetime", False, True, True),
        ("Lifetime", True, False, False),
    ],
)
@pytest.mark.usefixtures("mock_respond", "mock_char_save")
async def test_award_respects_permissions(
    vamp: VChar,
    ctx: AppCtx,
    user: discord.Member,
    mock_error: AsyncMock,
    scope: str,
    unspent_ok: bool,
    lifetime_ok: bool,
    allowed: bool,
):
    """Players can award XP only in the scopes the server allows."""
    unspent_patch, lifetime_patch = _permissions(unspent_ok, lifetime_ok)
    with unspent_patch, lifetime_patch:
        await award_or_deduct(ctx, vamp, 5, scope, "Test", player=user)

    if allowed:
        assert vamp.experience.unspent == 5
        assert len(vamp.experience.log) == 1
        mock_error.assert_not_awaited()
    else:
        assert vamp.experience.unspent == 0
        assert vamp.experience.lifetime == 0
        assert not vamp.experience.log
        mock_error.assert_awaited_once()
