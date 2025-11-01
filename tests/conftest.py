"""Pytest configuration."""

import asyncio
import os
from typing import cast

import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

import inconnu.db

os.environ["PYTEST"] = "1"
os.environ["ADMIN_SERVER"] = "09876"
os.environ["SUPPORTER_ROLE"] = "12345"
os.environ["SUPPORTER_GUILD"] = "54321"


@pytest.fixture(autouse=True, scope="session")
async def beanie_fixture():
    """Configures a mock beanie client for all tests."""
    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    db = client.test
    await init_beanie(db, document_models=inconnu.db.models())


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop to share between tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
