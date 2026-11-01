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


@pytest.fixture
def rouse_only(character: VChar) -> VChar:
    """The character, with a macro that only makes a Rouse Check."""
    character.add_macro(
        name="rouse",
        pool=[],
        hunger=True,
        difficulty=0,
        rouses=1,
        reroll_rouses=False,
        staining="no",
        hunt=False,
        comment=None,
    )
    return character


async def test_emptying_macro_refused(ctx: AppCtx, rouse_only: VChar, mock_error: AsyncMock):
    """Removing the Rouse Checks from a macro without a pool is refused."""
    await update(ctx, rouse_only, "rouse", "rouses=0")

    mock_error.assert_awaited_once()
    assert "needs a pool or Rouse Checks" in str(mock_error.call_args.args[1])
    assert rouse_only.find_macro("rouse").rouses == 1


async def test_removing_rouses_with_pool(ctx: AppCtx, rouse_only: VChar, mock_error: AsyncMock):
    """Removing the Rouse Checks is fine if the same update adds a pool."""
    with patch.object(VChar, "save", new_callable=AsyncMock):
        await update(ctx, rouse_only, "rouse", "rouses=0 pool=strength")

    mock_error.assert_not_awaited()
    macro = rouse_only.find_macro("rouse")
    assert macro.rouses == 0
    assert macro.pool == ["Strength"]
