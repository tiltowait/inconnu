"""Route test configurations."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from bot import InconnuBot
from routes.deps import get_bot
from server import app


@pytest.fixture(autouse=True)
def _app_bot() -> Generator[MagicMock, None, None]:
    """Give the routes a bot. Tests can override get_bot again with their own."""
    bot = MagicMock(spec=InconnuBot)
    with patch.dict(app.dependency_overrides, {get_bot: lambda: bot}):
        yield bot
