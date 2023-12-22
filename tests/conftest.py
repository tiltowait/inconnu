"""Pytest configuration."""

import asyncio
import os

import pytest
from mongomock_motor import AsyncMongoMockClient

import inconnu

os.environ["PYTEST"] = "1"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop to share between tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def beanie_fixture():
    """Configures a mock beanie client for all tests."""
    client = AsyncMongoMockClient()
    await inconnu.db.init_db("test", client)
