"""Test bot settings."""

import pytest

import inconnu
from inconnu import VUser


@pytest.fixture
async def user():
    user = VUser(user=1234)
    await user.insert()
    return user


async def test_fetch_user(user):
    fetched = await VUser.find_one(VUser.user == user.user)
    assert fetched.user == user.user

    assert await VUser.find_one(VUser.user == 0) is None


async def test_find_user_creates_user():
    uid = 1

    assert await VUser.find_one(VUser.user == uid) is None

    user = await inconnu.settings.find_user(uid)
    assert isinstance(user, VUser)
    assert user.user == uid

    found = await VUser.find_one(VUser.user == uid)
    assert user.id == found.id
    assert user.user == found.user


async def test_find_user_creates_only_one_user():
    uid = 2

    for _ in range(10):
        user = await inconnu.settings.find_user(uid)
        assert user is not None

    assert await VUser.count() == 1
