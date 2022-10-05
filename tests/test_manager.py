"""Test character manager fetching."""
# pylint: disable=too-few-public-methods

import unittest
from types import SimpleNamespace

import inconnu

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
        self.id = user_id  # pylint: disable=invalid-name
        self.top_role = SimpleNamespace(permissions=MockPermissions(admin))
        self.guild_permissions = MockPermissions(admin)


class TestManagerPermissions(unittest.IsolatedAsyncioTestCase):
    """Test the CharacterManager fetch permissions."""

    GUILD = 1
    USER = 1
    CHAR_NAME = "Test"
    CHAR_ID = "633cd0461b6d765e70385f80"
    WRONG_GUILD = 2
    WRONG_USER = 2

    async def test_management(self):
        """Run a battery of CharManager tests."""
        # A collision between the unit test closing the running loop each test
        # and the architecture of umongo + the bot means we have to put
        # everything into the same test case. We could probably avoid this with
        # pytest, but for now we'll keep with the built-in unit testing
        # framework.

        user = MockUser(self.USER, False)
        char = await inconnu.char_mgr.fetchone(self.GUILD, user, self.CHAR_NAME)
        self.assertIsNotNone(char)

        # Wrong user, right guild, no admin
        user = MockUser(self.WRONG_USER, False)
        with self.assertRaises(inconnu.errors.CharacterNotFoundError):
            _ = await inconnu.char_mgr.fetchone(self.GUILD, user, self.CHAR_NAME)

        # Right user, wrong guild
        user = MockUser(self.USER, False)
        with self.assertRaises(inconnu.errors.CharacterNotFoundError):
            _ = await inconnu.char_mgr.fetchone(self.WRONG_GUILD, user, self.CHAR_NAME)

        # Wrong user, wrong guild
        user = MockUser(self.WRONG_USER, False)
        with self.assertRaises(inconnu.errors.CharacterNotFoundError):
            _ = await inconnu.char_mgr.fetchone(self.WRONG_GUILD, user, self.CHAR_NAME)

        # Wrong user, right guild, admin
        user = MockUser(self.WRONG_USER, True)
        inconnu.char_mgr.bot = MockBot(user)
        char = await inconnu.char_mgr.fetchone(self.GUILD, user, self.CHAR_ID)
        self.assertIsNotNone(char)

        # Wrong user, wrong guild, admin
        user = MockUser(self.WRONG_USER, True)
        with self.assertRaises(LookupError):
            _ = await inconnu.char_mgr.fetchone(self.WRONG_GUILD, user, self.CHAR_ID)

        # Right user, wrong guild, admin
        user = MockUser(self.USER, True)
        with self.assertRaises(LookupError):
            _ = await inconnu.char_mgr.fetchone(self.WRONG_GUILD, user, self.CHAR_ID)
