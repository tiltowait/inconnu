"""Tests for interface/tasks.py's scheduled task startup."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import interface.tasks as tasks_module
from bot import InconnuBot
from interface.tasks import TasksCog


@pytest.fixture
async def cog() -> AsyncGenerator[TasksCog, None]:
    """A TasksCog whose loops are stopped afterward."""
    cog = TasksCog(MagicMock(spec=InconnuBot))
    yield cog
    cog.cog_unload()


async def test_on_ready_starts_tasks_once(cog: TasksCog):
    """Both tasks start on the first ready, and later readies leave them alone."""
    # Patch the module TasksCog came from; loading the bot's cogs re-imports it
    with patch.object(tasks_module, "logger") as mock_logger:
        await cog.on_ready()
        await cog.on_ready()  # Would raise if the loops were started again

    assert cog.cull_inactive.is_running()
    assert cog.check_premium_expiries.is_running()

    logged = [c.args[1] for c in mock_logger.info.call_args_list]
    assert logged == ["cull_inactive", "check_premium_expiries"]


async def test_cog_unload_stops_tasks(cog: TasksCog):
    """Unloading the cog stops both tasks."""
    await cog.on_ready()
    cog.cog_unload()
    await asyncio.sleep(0)  # Let the cancellations land

    assert not cog.cull_inactive.is_running()
    assert not cog.check_premium_expiries.is_running()


async def test_cull_inactive_runs_cull(cog: TasksCog):
    """The cull task runs the cull job."""
    with patch("tasks.cull", new_callable=AsyncMock) as mock_cull:
        await cog.cull_inactive()

    mock_cull.assert_awaited_once()


async def test_check_premium_expiries_removes_images(cog: TasksCog):
    """The premium task removes expired supporters' images."""
    with patch("tasks.premium.remove_expired_images", new_callable=AsyncMock) as mock_remove:
        await cog.check_premium_expiries()

    mock_remove.assert_awaited_once()
