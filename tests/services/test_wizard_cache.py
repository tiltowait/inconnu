"""Basic WizardCache tests."""

from unittest.mock import MagicMock

import pytest
from discord import Guild

from services.wizard import WizardCache, WizardData

USER = 2


@pytest.fixture
def guild() -> Guild:
    guild = MagicMock(spec=Guild)
    guild.id = 1
    guild.name = "Test Guild"
    guild.icon.url = "https://example.com/guild.png"

    return guild


@pytest.fixture
def uk(guild: Guild) -> tuple[int, int]:
    return (guild.id, USER)


@pytest.fixture
def wc() -> WizardCache:
    return WizardCache()


def test_registration(wc: WizardCache, guild: Guild, uk: tuple[int, int]):
    key = wc.register(guild, USER, False)
    assert key in wc.cache
    assert uk in wc.users
    assert isinstance(wc.get(key), WizardData)


def test_anti_spam(wc: WizardCache, guild: Guild):
    key1 = wc.register(guild, USER, False)
    key2 = wc.register(guild, USER, False)
    assert key1 == key2

    key3 = wc.register(guild, USER, True)
    assert key3 != key1

    guild.id = 5
    key4 = wc.register(guild, USER, False)
    assert key4 != key1 and key4 != key3

    assert wc.count == 3


def test_delete(wc: WizardCache, guild: Guild, uk: tuple[int, int]):
    key = wc.register(guild, USER, False)
    wc.delete(key)
    assert key not in wc.cache
    assert uk not in wc.users
