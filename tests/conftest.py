"""Pytest configuration."""

import os
from typing import cast

import mongomock
import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

os.environ["PYTEST"] = "1"

# beanie 2.1.0 passes authorizedCollections/nameOnly kwargs that mongomock doesn't support
_orig_list_collection_names = mongomock.Database.list_collection_names


def _patched_list_collection_names(self, filter=None, session=None, **kwargs):
    return _orig_list_collection_names(self, filter=filter, session=session)


mongomock.Database.list_collection_names = _patched_list_collection_names
os.environ["ADMIN_SERVER"] = "09876"
os.environ["SUPPORTER_ROLE"] = "12345"
os.environ["SUPPORTER_GUILD"] = "54321"
os.environ["INCONNU_TOKEN"] = "test-token"  # Never use the real bot token in tests
os.environ.setdefault("MONGO_URL", "mongodb://localhost/test")


@pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
async def beanie_fixture():
    """Configures a mock beanie client for all tests."""
    import db as database

    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    mock_db = client.test
    await init_beanie(mock_db, document_models=database.models())
