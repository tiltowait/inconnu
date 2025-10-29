"""Pytest configuration."""

import asyncio
import os

import pytest

os.environ["PYTEST"] = "1"
os.environ["ADMIN_SERVER"] = "09876"
os.environ["SUPPORTER_ROLE"] = "12345"
os.environ["SUPPORTER_GUILD"] = "54321"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop to share between tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
