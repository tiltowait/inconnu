"""Frenzy check tests."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from ctx import AppCtx
from inconnu.misc.frenzy import frenzy
from models.vchar import VChar


@pytest.fixture(autouse=True)
def mock_display() -> Iterator[None]:
    """Show the outcome as an embed, without sending anything."""
    with (
        patch("services.settings.accessible", new_callable=AsyncMock, return_value=False),
        patch("ctx.AppCtx.respond", new_callable=AsyncMock),
        patch("inconnu.misc.frenzy.get_message", new_callable=AsyncMock),
    ):
        yield


@pytest.mark.parametrize(
    "die,difficulty,title,color",
    [
        (6, 1, "Frenzy Success", None),
        (5, 1, "Frenzy Failure", 0x880000),  # No successes
        (6, 10, "Frenzy Failure", 0x880000),  # Some successes, but not enough
    ],
)
async def test_frenzy_report(
    die: int,
    difficulty: int,
    title: str,
    color: int | None,
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
    mock_common_report: AsyncMock,
):
    """Every failure, including one with no successes, is reported in red."""
    with patch("inconnu.d10", side_effect=lambda count: [die] * count):
        await frenzy(ctx, vamp, difficulty, None, None)

    assert mock_common_report.await_args is not None
    kwargs = mock_common_report.await_args.kwargs
    assert kwargs["title"] == title
    assert kwargs["color"] == color
