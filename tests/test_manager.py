"""Test character manager fetching."""

from types import SimpleNamespace

import pytest
import pytest_asyncio

import constants
import inconnu
from errors import CharacterNotFoundError
from models import VChar

GUILD = 1
USER = 1
CHAR_NAME = "Test"
WRONG_GUILD = 2
WRONG_USER = 2

# We have to make a bunch of mock classes in order to fool the CharacterManager
# into letting us fetch characters.


class MockGuild:
    """A phony Guild."""

    def __init__(self, user):
        self.user = user

    def get_member(self, _):
        """Get the user object."""
        return self.user


class MockBot:
    """A phony bot."""

    def __init__(self, user):
        self.mock_guild = MockGuild(user)

    def get_guild(self, _):
        """Return a fake guild object."""
        return self.mock_guild


class MockPermissions:
    """A class that mocks user permissions based on a single mask."""

    def __init__(self, permit: bool):
        self.permit = permit

    def __getattr__(self, attr: str):
        return self.permit


class MockUser:
    """Mock user object that has fake permissions."""

    def __init__(self, user_id: int, admin: bool):
        self.id = user_id
        self.top_role = SimpleNamespace(permissions=MockPermissions(admin))
        self.guild_permissions = MockPermissions(admin)


@pytest_asyncio.fixture(scope="module")
async def char_id() -> str:
    """The ID of a dummy character inserted into the database."""
    splat = "vampire"
    char = VChar(
        guild=1,
        user=1,
        raw_name="Test",
        splat=splat,
        raw_humanity=7,
        health=6 * constants.Damage.NONE,
        willpower=5 * constants.Damage.NONE,
        potency=splat == "vampire" and 1 or 0,
    )
    await char.save()
    yield char.id_str
    await char.delete()


@pytest.mark.parametrize(
    "user_id,admin,guild,exception",
    [
        (USER, False, GUILD, None),
        (WRONG_USER, False, GUILD, CharacterNotFoundError),
        (USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, False, WRONG_GUILD, CharacterNotFoundError),
        (WRONG_USER, True, GUILD, None),
        (WRONG_USER, True, WRONG_GUILD, LookupError),
        (USER, True, WRONG_GUILD, LookupError),
    ],
)
@pytest.mark.asyncio
async def test_management(
    user_id: int, admin: bool, guild: int, exception: Exception, char_id: str
):
    """Run a battery of CharManager tests."""
    user = MockUser(user_id, admin)
    inconnu.char_mgr.bot = MockBot(user)  # Establish admin (or not)
    identifier = char_id if admin else CHAR_NAME

    if exception is not None:
        with pytest.raises(exception):
            _ = await inconnu.char_mgr.fetchone(guild, user, identifier)
    else:
        char = await inconnu.char_mgr.fetchone(guild, user, identifier)
        assert char is not None
