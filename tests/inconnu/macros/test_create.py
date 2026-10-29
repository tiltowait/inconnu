"""Tests for inconnu/macros/create.py."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ctx import AppCtx
from inconnu.macros.create import create
from models import VChar
from tests.characters import gen_char


@pytest.fixture
def character() -> VChar:
    """A vampire with traits to build pools from."""
    char = gen_char("vampire")
    char.assign_traits({"Strength": 3, "Brawl": 2})
    return char


@pytest.fixture
def ctx() -> AppCtx:
    """The /macro create invocation."""
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
    """Roll errors in the pool are shown to the user, and no macro is made."""
    await create(ctx, character, "test", pool, True, 0, 0, False, "no", False, None)

    mock_error.assert_awaited_once()
    assert not character.macros
