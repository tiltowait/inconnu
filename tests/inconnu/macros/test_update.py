"""Tests for inconnu/macros/update.py."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ctx import AppCtx
from inconnu.macros.update import update
from models import VChar
from tests.characters import gen_char


@pytest.fixture
def character() -> VChar:
    """A vampire with a macro to update."""
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 2})
    char.add_macro(
        name="test",
        pool=["Strength"],
        hunger=True,
        difficulty=0,
        rouses=0,
        reroll_rouses=False,
        staining="no",
        hunt=False,
        comment=None,
    )
    return char


@pytest.fixture
def ctx() -> AppCtx:
    """The /macro update invocation."""
    ctx = MagicMock(spec=AppCtx)
    ctx.respond = AsyncMock()  # A property on ApplicationContext, so the spec can't infer it
    return ctx


@pytest.fixture
def mock_error() -> Iterator[AsyncMock]:
    """Capture error messages."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.parametrize(
    "pool",
    [
        "strength brawl",  # Missing +, so brawl is read as Hunger
        "strength brawl 2 3",  # Too many parameters
        "strength 2 brawl",  # Non-numeric Difficulty
        "strength + hunger",  # Hunger in the pool
    ],
)
async def test_invalid_pool_shows_error(
    ctx: AppCtx, character: VChar, mock_error: AsyncMock, pool: str
):
    """Roll errors in the new pool are shown to the user, and the macro is unchanged."""
    await update(ctx, character, "test", f"pool={pool}")

    mock_error.assert_awaited_once()
    assert character.find_macro("test").pool == ["Strength"]
