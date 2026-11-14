"""Tests for models/vuser.py."""

import asyncio

from models import VUser

USER_ID = 4815162342


async def test_get_or_fetch_saves_new_user_once():
    """Simultaneous lookups of a new user share one saved document. An unsaved
    one would be inserted by each of its simultaneous saves."""
    VUser.get_or_fetch.cache_clear()
    await VUser.find({"user": USER_ID}).delete()

    users = await asyncio.gather(*(VUser.get_or_fetch(USER_ID) for _ in range(5)))

    assert all(user is users[0] for user in users)
    assert users[0].id is not None
    assert await VUser.find({"user": USER_ID}).count() == 1
