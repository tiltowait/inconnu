"""Comprehensive tests for CharacterManager."""

from types import SimpleNamespace

import pytest
import pytest_asyncio

from inconnu.constants import Damage
from errors import (
    NoCharactersError,
    UnspecifiedCharacterError,
)
from models import VChar
from caches import CharacterManager

# Mock classes for admin testing


class MockPermissions:
    """Mock Discord permissions."""

    def __init__(self, is_admin: bool):
        self.administrator = is_admin


class MockRole:
    """Mock Discord role."""

    def __init__(self, is_admin: bool):
        self.permissions = MockPermissions(is_admin)


class MockMember:
    """Mock Discord member."""

    def __init__(self, user_id: int, is_admin: bool):
        self.id = user_id
        self.top_role = MockRole(is_admin)
        self.guild_permissions = MockPermissions(is_admin)


class MockGuild:
    """Mock Discord guild."""

    def __init__(self, guild_id: int, members: dict):
        self.id = guild_id
        self._members = members

    def get_member(self, user_id: int):
        return self._members.get(user_id)


class MockBot:
    """Mock Discord bot."""

    def __init__(self, guilds: dict):
        self.user = SimpleNamespace(id=0)
        self._guilds = guilds

    def get_guild(self, guild_id: int):
        return self._guilds.get(guild_id)


# Fixtures


@pytest_asyncio.fixture
async def manager():
    """Create a fresh CharacterManager instance."""
    mgr = CharacterManager()
    # Clear the in-memory cache only - do NOT delete database records
    mgr.user_cache.clear()
    mgr.id_cache.clear()
    mgr.all_fetched.clear()
    return mgr


@pytest_asyncio.fixture
async def char1():
    """Create first test character (Alice)."""
    char = VChar(
        guild=1,
        user=1,
        name="Alice",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    yield char
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def char2():
    """Create second test character (Bob)."""
    char = VChar(
        guild=1,
        user=1,
        name="Bob",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    yield char
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def char3():
    """Create third test character (Charlie, different user)."""
    char = VChar(
        guild=1,
        user=2,
        name="Charlie",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    yield char
    try:
        await char.delete()
    except Exception:
        pass


# CHARACTER_COUNT TESTS


async def test_character_count_zero(manager):
    """Test character_count with no characters."""
    count = await manager.character_count(1, 999)
    assert count == 0


async def test_character_count_one(manager, char1):
    """Test character_count with one character."""
    count = await manager.character_count(1, 1)
    assert count == 1


async def test_character_count_multiple(manager, char1, char2):
    """Test character_count with multiple characters."""
    count = await manager.character_count(1, 1)
    assert count == 2


async def test_character_count_different_users(manager, char1, char3):
    """Test character_count counts only the specified user."""
    count = await manager.character_count(1, 1)
    assert count == 1

    count = await manager.character_count(1, 2)
    assert count == 1


# EXISTS TESTS


async def test_exists_no_character(manager):
    """Test exists returns False when character doesn't exist."""
    manager.bot = MockBot({})
    exists = await manager.exists(1, 1, "NonExistent", False)
    assert exists is False


async def test_exists_character_found(manager, char1):
    """Test exists returns True when character exists."""
    manager.bot = MockBot({})
    exists = await manager.exists(1, 1, "Alice", False)
    assert exists is True


async def test_exists_case_insensitive(manager, char1):
    """Test exists is case-insensitive."""
    manager.bot = MockBot({})
    exists = await manager.exists(1, 1, "alice", False)
    assert exists is True

    exists = await manager.exists(1, 1, "ALICE", False)
    assert exists is True


async def test_exists_spc(manager):
    """Test exists with SPC flag."""
    # Create an SPC - the name property will automatically append " (SPC)"
    spc = VChar(
        guild=1,
        user=0,  # SPC_OWNER - makes this an SPC
        name="Example",  # VChar.name property will return "Example (SPC)"
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await spc.insert()

    manager.bot = MockBot({})

    # exists() will append " (SPC)" to "Example", making it "Example (SPC)"
    # This matches the SPC's name property which also returns "Example (SPC)"
    exists = await manager.exists(1, 1, "Example", True)
    assert exists is True

    # Test that it doesn't find non-existent SPC
    exists = await manager.exists(1, 1, "NonExistent", True)
    assert exists is False

    await spc.delete()


async def test_exists_different_user(manager, char1):
    """Test exists returns False for different user."""
    manager.bot = MockBot({})
    exists = await manager.exists(1, 2, "Alice", False)
    assert exists is False


# REGISTER TESTS


async def test_register_adds_to_id_cache(manager):
    """Test register adds character to ID cache."""
    char = VChar(
        guild=1,
        user=1,
        name="NewChar",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()

    # Fetch to populate cache first
    await manager.fetchall(1, 1)

    assert char.id_str in manager.id_cache
    assert manager.id_cache[char.id_str].id == char.id

    await char.delete()


async def test_register_adds_to_user_cache(manager):
    """Test register adds character to user cache."""
    char = VChar(
        guild=1,
        user=1,
        name="NewChar",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()

    await manager.register(char)

    key = "1 1"
    assert key in manager.user_cache
    assert char in manager.user_cache[key]

    await char.delete()


async def test_register_maintains_sorted_order(manager, char1):
    """Test register maintains alphabetical order."""
    # Load char1 into cache first
    await manager.fetchall(1, 1)

    # char1 is "Alice", add "Charlie" which should come after
    charlie = VChar(
        guild=1,
        user=1,
        name="Charlie",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await charlie.insert()

    await manager.register(charlie)

    key = "1 1"
    chars = manager.user_cache[key]
    assert len(chars) == 2
    assert chars[0].name == "Alice"
    assert chars[1].name == "Charlie"

    await charlie.delete()


async def test_register_inserts_in_middle(manager, char1, char2):
    """Test register inserts character in correct alphabetical position."""
    # Load existing characters into cache first
    await manager.fetchall(1, 1)

    # char1 = Alice, char2 = Bob, insert "Amy" between them
    amy = VChar(
        guild=1,
        user=1,
        name="Amy",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await amy.insert()

    await manager.register(amy)

    key = "1 1"
    chars = manager.user_cache[key]
    assert len(chars) == 3
    assert chars[0].name == "Alice"
    assert chars[1].name == "Amy"
    assert chars[2].name == "Bob"

    await amy.delete()


# REMOVE TESTS


async def test_remove_deletes_from_database(manager, char1):
    """Test remove deletes character from database."""
    char_id = char1.id

    result = await manager.remove(char1)
    assert result is True

    # Verify it's gone from database
    fetched = await VChar.get(char_id)
    assert fetched is None


async def test_remove_removes_from_id_cache(manager, char1):
    """Test remove removes character from ID cache."""
    char_id_str = char1.id_str
    await manager.fetchall(1, 1)  # Populate cache

    assert char_id_str in manager.id_cache

    await manager.remove(char1)

    assert char_id_str not in manager.id_cache


async def test_remove_removes_from_user_cache(manager, char1):
    """Test remove removes character from user cache."""
    chars = await manager.fetchall(1, 1)  # Populate cache
    cached_char = chars[0]  # Get the cached instance

    key = "1 1"
    assert cached_char in manager.user_cache[key]

    await manager.remove(cached_char)

    assert cached_char not in manager.user_cache[key]


async def test_remove_updates_user_cache_list(manager, char1, char2):
    """Test remove properly updates user cache list."""
    chars = await manager.fetchall(1, 1)  # Populate cache
    cached_alice = chars[0]  # Alice is first alphabetically

    key = "1 1"
    assert len(manager.user_cache[key]) == 2

    await manager.remove(cached_alice)

    assert len(manager.user_cache[key]) == 1
    assert manager.user_cache[key][0].name == "Bob"


async def test_remove_nonexistent_character(manager):
    """Test remove returns False for already-deleted character."""
    char = VChar(
        guild=999,
        user=999,
        name="Ghost",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()

    # Delete it first
    await char.delete()

    # Try to remove again
    result = await manager.remove(char)
    assert result is False


# TRANSFER TESTS


async def test_transfer_updates_character_user(manager, char1):
    """Test transfer updates character's user field."""
    # Load into cache first
    chars = await manager.fetchall(1, 1)
    cached_char = chars[0]

    new_owner = SimpleNamespace(id=2, name="NewOwner")
    current_owner = SimpleNamespace(id=1, name="OldOwner")

    await manager.transfer(cached_char, current_owner, new_owner)

    assert cached_char.user == 2

    # Verify in database
    fetched = await VChar.get(cached_char.id)
    assert fetched is not None
    assert fetched.user == 2


async def test_transfer_removes_from_old_cache(manager, char1, char2):
    """Test transfer removes character from old owner's cache."""
    chars = await manager.fetchall(1, 1)  # Populate cache
    cached_alice = chars[0]  # Alice

    old_key = "1 1"
    assert len(manager.user_cache[old_key]) == 2

    new_owner = SimpleNamespace(id=2, name="NewOwner")
    current_owner = SimpleNamespace(id=1, name="OldOwner")

    await manager.transfer(cached_alice, current_owner, new_owner)

    # Old owner should have one less character
    assert len(manager.user_cache[old_key]) == 1
    assert manager.user_cache[old_key][0].name == "Bob"


async def test_transfer_adds_to_new_cache_if_loaded(manager, char1, char3):
    """Test transfer adds to new owner's cache if already loaded."""
    # Load both users' caches
    chars1 = await manager.fetchall(1, 1)
    await manager.fetchall(1, 2)

    cached_alice = chars1[0]

    new_key = "1 2"
    assert len(manager.user_cache[new_key]) == 1  # Just Charlie

    new_owner = SimpleNamespace(id=2, name="NewOwner")
    current_owner = SimpleNamespace(id=1, name="OldOwner")

    await manager.transfer(cached_alice, current_owner, new_owner)

    # New owner should have both characters, sorted
    assert len(manager.user_cache[new_key]) == 2
    assert manager.user_cache[new_key][0].name == "Alice"
    assert manager.user_cache[new_key][1].name == "Charlie"


async def test_transfer_doesnt_add_if_cache_not_loaded(manager, char1):
    """Test transfer doesn't add to new owner's cache if not loaded."""
    # Don't load user 2's cache
    chars = await manager.fetchall(1, 1)
    cached_alice = chars[0]

    new_owner = SimpleNamespace(id=2, name="NewOwner")
    current_owner = SimpleNamespace(id=1, name="OldOwner")

    await manager.transfer(cached_alice, current_owner, new_owner)

    # New owner's cache shouldn't exist
    new_key = "1 2"
    assert manager.user_cache.get(new_key) is None


# MARK_INACTIVE / MARK_ACTIVE TESTS


async def test_mark_inactive(manager, char1):
    """Test mark_inactive sets the left timestamp."""
    pytest.skip("mongomock_motor doesn't support nested field $set operations")
    player = SimpleNamespace(guild=SimpleNamespace(id=1), id=1)

    await manager.mark_inactive(player)

    # Verify in database
    fetched = await VChar.get(char1.id)
    assert fetched is not None
    assert "left" in fetched.stat_log


async def test_mark_active(manager, char1):
    """Test mark_active removes the left timestamp."""
    pytest.skip("mongomock_motor doesn't support nested field $set operations")
    player = SimpleNamespace(guild=SimpleNamespace(id=1), id=1)

    # First mark inactive
    await manager.mark_inactive(player)
    fetched = await VChar.get(char1.id)
    assert fetched is not None
    assert "left" in fetched.stat_log

    # Then mark active
    await manager.mark_active(player)
    fetched = await VChar.get(char1.id)
    assert fetched is not None
    assert "left" not in fetched.stat_log


# SORT_USER TESTS


async def test_sort_user_sorts_cache(manager, char1, char2):
    """Test sort_user sorts the user's characters."""
    await manager.fetchall(1, 1)

    # Manually disorder the cache
    key = "1 1"
    manager.user_cache[key].reverse()
    assert manager.user_cache[key][0].name == "Bob"

    # Sort it
    manager.sort_user(1, 1)

    assert manager.user_cache[key][0].name == "Alice"
    assert manager.user_cache[key][1].name == "Bob"


async def test_sort_user_no_cache(manager):
    """Test sort_user does nothing if cache not loaded."""
    # Don't load cache
    manager.sort_user(1, 1)
    # Should not crash


# FETCHONE EDGE CASES


async def test_fetchone_vchar_passthrough(manager, char1):
    """Test fetchone returns VChar unchanged."""
    result = await manager.fetchone(1, 1, char1)
    assert result is char1


async def test_fetchone_no_characters_error(manager):
    """Test fetchone raises NoCharactersError when user has no characters."""
    with pytest.raises(NoCharactersError) as exc_info:
        await manager.fetchone(1, 999, None)
    assert "no characters" in str(exc_info.value).lower()


async def test_fetchone_multiple_characters_error(manager, char1, char2):
    """Test fetchone raises UnspecifiedCharacterError with multiple characters."""
    with pytest.raises(UnspecifiedCharacterError) as exc_info:
        await manager.fetchone(1, 1, None)
    assert "specify which" in str(exc_info.value).lower()


async def test_fetchone_single_character_auto_select(manager, char1):
    """Test fetchone auto-selects when user has exactly one character."""
    result = await manager.fetchone(1, 1, None)
    assert result.id == char1.id
    assert result.name == char1.name


# FETCHALL CACHE HIT TESTS


async def test_fetchall_cache_hit(manager, char1):
    """Test fetchall returns from cache on second call."""
    # First call - fetches from database
    chars1 = await manager.fetchall(1, 1)
    assert len(chars1) == 1

    # Verify cache is populated
    key = "1 1"
    assert manager.all_fetched.get(key) is True

    # Second call - should return from cache (not hit database again)
    chars2 = await manager.fetchall(1, 1)
    assert len(chars2) == 1
    assert chars2 is manager.user_cache.get(key)


async def test_fetchall_already_cached_character(manager, char1):
    """Test fetchall uses already-cached character from ID cache."""
    # Manually add to ID cache
    manager.id_cache[char1.id_str] = char1

    # Now fetch all - should use the cached instance
    chars = await manager.fetchall(1, 1)
    assert len(chars) == 1
    assert chars[0] is char1  # Same instance


# HELPER METHOD TESTS


def test_get_ids_with_objects():
    """Test _get_ids extracts IDs from objects."""
    guild_obj = SimpleNamespace(id=123)
    user_obj = SimpleNamespace(id=456)

    guild, user, key = CharacterManager._get_ids(guild_obj, user_obj)

    assert guild == 123
    assert user == 456
    assert key == "123 456"


def test_get_ids_with_ints():
    """Test _get_ids handles integers."""
    guild, user, key = CharacterManager._get_ids(123, 456)

    assert guild == 123
    assert user == 456
    assert key == "123 456"


def test_user_key():
    """Test _user_key generates correct key."""
    char = SimpleNamespace(guild=123, user=456)
    key = CharacterManager._user_key(char)
    assert key == "123 456"


def test_is_admin_no_bot(manager):
    """Test _is_admin returns False when bot is None."""
    result = manager._is_admin(1, 1)
    assert result is False


def test_is_admin_true(manager):
    """Test _is_admin returns True for administrator."""
    member = MockMember(1, is_admin=True)
    guild = MockGuild(1, {1: member})
    manager.bot = MockBot({1: guild})

    result = manager._is_admin(1, 1)
    assert result is True


def test_is_admin_false(manager):
    """Test _is_admin returns False for non-administrator."""
    member = MockMember(1, is_admin=False)
    guild = MockGuild(1, {1: member})
    manager.bot = MockBot({1: guild})

    result = manager._is_admin(1, 1)
    assert result is False


async def test_validate_admin_bypass(manager, char3):
    """Test _validate allows admin to access other users' characters."""
    # char3 belongs to user 2
    # Create admin user 1
    admin = MockMember(1, is_admin=True)
    guild = MockGuild(1, {1: admin})
    manager.bot = MockBot({1: guild})

    # Admin should be able to validate char3 even though it's user 2's
    try:
        manager._validate(1, 1, char3)
        # Should not raise
    except LookupError:
        pytest.fail("Admin should be able to access other users' characters")
