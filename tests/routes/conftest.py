"""Route test configurations."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _ensure_inconnu_bot():
    """Ensure inconnu.bot exists so patch() targets can resolve it."""
    with patch("inconnu.bot", MagicMock(), create=True):
        yield
