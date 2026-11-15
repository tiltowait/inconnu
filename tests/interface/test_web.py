"""Tests for interface/web.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import uvicorn

import interface.web as web_module
from bot import InconnuBot
from events import CharEvents
from interface.web import APIServer, WebCog
from server import app


async def test_shutdown_ends_event_streams():
    """Shutting down closes the event streams before waiting on connections."""
    server = APIServer(uvicorn.Config(app))
    with (
        patch.object(web_module, "char_events", spec=CharEvents) as mock_events,
        patch.object(uvicorn.Server, "shutdown", new_callable=AsyncMock) as mock_shutdown,
    ):
        await server.shutdown()

    mock_events.close.assert_called_once_with()
    mock_shutdown.assert_awaited_once_with(None)


async def test_startup_allows_event_streams():
    """Starting up reopens the event streams an earlier server closed."""
    server = APIServer(uvicorn.Config(app))
    with (
        patch.object(web_module, "char_events", spec=CharEvents) as mock_events,
        patch.object(uvicorn.Server, "startup", new_callable=AsyncMock) as mock_startup,
    ):
        await server.startup()

    mock_events.open.assert_called_once_with()
    mock_startup.assert_awaited_once_with(None)


def test_unload_shuts_down_gracefully():
    """Unloading asks the server to exit, so its shutdown ends the streams,
    rather than cancelling it."""
    cog = WebCog(MagicMock(spec=InconnuBot))
    cog.server = APIServer(uvicorn.Config(app))
    cog.server_task = MagicMock(spec=asyncio.Task)

    cog.cog_unload()

    assert cog.server.should_exit
    cog.server_task.cancel.assert_not_called()
