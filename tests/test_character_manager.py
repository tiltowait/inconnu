"""Behavioral tests for CharacterManager."""

import pytest
import pytest_asyncio
import discord
from unittest.mock import MagicMock

from constants import Damage
from errors import CharacterNotFoundError, UnspecifiedCharacterError, DuplicateCharacterError
from models import VChar
from services import CharacterManager


def mock_member(user_id: int, guild_id: int, is_admin: bool = False) -> discord.Member:
    """Create a mock Discord member with permissions."""
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.guild.id = guild_id

    permissions = MagicMock(spec=discord.Permissions)
    permissions.administrator = is_admin

    member.top_role.permissions = permissions
    member.guild_permissions = permissions

    return member


def mock_guild(guild_id: int) -> discord.Guild:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    return guild


# Fixtures


@pytest_asyncio.fixture
async def manager():
    """Create a fresh CharacterManager instance."""
    mgr = CharacterManager()
    await mgr.initialize()
    return mgr


@pytest_asyncio.fixture
async def char1():
    """Create first test character (Alice) - not yet in database."""
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
    # Don't insert - tests will register or insert as needed
    yield char
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def char2():
    """Create second test character (Bob) - not yet in database."""
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
    # Don't insert - tests will register or insert as needed
    yield char
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def char3():
    """Create third test character (Charlie, different user) - not yet in database."""
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
    # Don't insert - tests will register or insert as needed
    yield char
    try:
        await char.delete()
    except Exception:
        pass


# INITIALIZE TESTS


async def test_initialize_loads_existing_characters():
    """Test initialize() loads characters that already exist in database."""
    # Create characters directly in database (before manager exists)
    alice = VChar(
        guild=1,
        user=1,
        name="Alice",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    bob = VChar(
        guild=1,
        user=1,
        name="Bob",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await alice.save()
    await bob.save()

    try:
        # Now create manager and initialize (cold start)
        mgr = CharacterManager()
        await mgr.initialize()

        # Verify manager loaded characters from database
        chars = await mgr.fetchall(1, 1)
        assert len(chars) == 2
        assert chars[0].name == "Alice"
        assert chars[1].name == "Bob"

        # Verify can fetch individual character
        char = await mgr.fetchone(mock_guild(1), mock_member(1, 1), "Alice")
        assert char.name == "Alice"

        # Verify id_fetch works
        alice_by_id = await mgr.id_fetch(alice.id)
        assert alice_by_id is not None
        assert alice_by_id.name == "Alice"

    finally:
        await alice.delete()
        await bob.delete()


# CHARACTER_COUNT TESTS


async def test_character_count_zero(manager):
    """Test character_count with no characters."""
    count = await manager.character_count(1, 999)
    assert count == 0


async def test_character_count_one(manager, char1):
    """Test character_count with one character."""
    await manager.register(char1)
    count = await manager.character_count(1, 1)
    assert count == 1


async def test_character_count_multiple(manager, char1, char2):
    """Test character_count with multiple characters."""
    await manager.register(char1)
    await manager.register(char2)
    count = await manager.character_count(1, 1)
    assert count == 2


async def test_character_count_different_users(manager, char1, char3):
    """Test character_count counts only the specified user."""
    await manager.register(char1)
    await manager.register(char3)

    count = await manager.character_count(1, 1)
    assert count == 1

    count = await manager.character_count(1, 2)
    assert count == 1


# FETCHALL TESTS


async def test_fetchall_empty(manager):
    """Test fetchall returns empty list when no characters exist."""
    chars = await manager.fetchall(1, 999)
    assert chars == []


async def test_fetchall_single(manager, char1):
    """Test fetchall returns single character."""
    await manager.register(char1)
    chars = await manager.fetchall(1, 1)
    assert len(chars) == 1
    assert chars[0].name == "Alice"


async def test_fetchall_multiple_sorted(manager, char1, char2):
    """Test fetchall returns characters in alphabetical order."""
    await manager.register(char2)  # Bob first
    await manager.register(char1)  # Alice second

    chars = await manager.fetchall(1, 1)
    assert len(chars) == 2
    assert chars[0].name == "Alice"  # Should be sorted
    assert chars[1].name == "Bob"


async def test_fetchall_filters_by_guild(manager, char1):
    """Test fetchall only returns characters from specified guild."""
    await manager.register(char1)

    # Same user, different guild
    chars = await manager.fetchall(999, 1)
    assert len(chars) == 0


async def test_fetchall_filters_by_user(manager, char1, char3):
    """Test fetchall only returns characters from specified user."""
    await manager.register(char1)
    await manager.register(char3)

    chars = await manager.fetchall(1, 1)
    assert len(chars) == 1
    assert chars[0].name == "Alice"


# EXISTS TESTS


async def test_exists_no_character(manager):
    """Test exists returns False when character doesn't exist."""
    guild = mock_guild(1)
    user = mock_member(1, 1)
    exists = await manager.exists(guild, user, "NonExistent", False)
    assert exists is False


async def test_exists_character_found(manager, char1):
    """Test exists returns True when character exists."""
    await manager.register(char1)
    guild = mock_guild(1)
    user = mock_member(1, 1)
    exists = await manager.exists(guild, user, "Alice", False)
    assert exists is True


async def test_exists_case_insensitive(manager, char1):
    """Test exists is case-insensitive."""
    await manager.register(char1)
    guild = mock_guild(1)
    user = mock_member(1, 1)

    assert await manager.exists(guild, user, "alice", False) is True
    assert await manager.exists(guild, user, "ALICE", False) is True
    assert await manager.exists(guild, user, "AlIcE", False) is True


async def test_exists_spc(manager):
    """Test exists with SPC flag uses correct owner."""
    # Create SPC character
    spc = VChar(
        guild=1,
        user=VChar.SPC_OWNER,
        name="TestNPC",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await manager.register(spc)

    guild = mock_guild(1)
    user = mock_member(1, 1)

    # Should find SPC when is_spc=True
    # Note: VChar.name property adds " (SPC)" suffix for non-PCs
    exists = await manager.exists(guild, user, "TestNPC (SPC)", True)
    assert exists is True

    await spc.delete()


# REGISTER TESTS


async def test_register_adds_character(manager):
    """Test register adds character to database."""
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
    await manager.register(char)

    # Verify it's in the database
    chars = await manager.fetchall(1, 1)
    assert len(chars) == 1
    assert chars[0].name == "NewChar"

    await char.delete()


async def test_register_maintains_sorted_order(manager, char1):
    """Test register maintains alphabetical order."""
    await manager.register(char1)  # Alice

    # Add Charlie (should come after)
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
    await manager.register(charlie)

    chars = await manager.fetchall(1, 1)
    assert len(chars) == 2
    assert chars[0].name == "Alice"
    assert chars[1].name == "Charlie"

    await charlie.delete()


async def test_register_inserts_in_middle(manager, char1, char2):
    """Test register maintains sorted order with insert in middle."""
    await manager.register(char1)  # Alice
    await manager.register(char2)  # Bob

    # Add Amy (should go between Alice and Bob)
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
    await manager.register(amy)

    chars = await manager.fetchall(1, 1)
    assert len(chars) == 3
    assert chars[0].name == "Alice"
    assert chars[1].name == "Amy"
    assert chars[2].name == "Bob"

    await amy.delete()


async def test_register_duplicate_raises_error(manager, char1):
    """Test register raises DuplicateCharacterError for duplicate names."""
    await manager.register(char1)

    # Try to register another character with same name
    duplicate = VChar(
        guild=1,
        user=1,
        name="Alice",  # Same name
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )

    with pytest.raises(DuplicateCharacterError):
        await manager.register(duplicate)


# REMOVE TESTS


async def test_remove_deletes_from_database(manager, char1):
    """Test remove deletes character from database."""
    await manager.register(char1)

    result = await manager.remove(char1)
    assert result is True

    # Verify it's gone
    chars = await manager.fetchall(1, 1)
    assert len(chars) == 0


async def test_remove_returns_true_on_success(manager, char1):
    """Test remove returns True when character is successfully deleted."""
    await manager.register(char1)
    result = await manager.remove(char1)
    assert result is True


async def test_remove_returns_false_on_failure(manager):
    """Test remove returns False when character doesn't exist."""
    # Create a character that's already been deleted
    char = VChar(
        guild=1,
        user=1,
        name="Deleted",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    await char.delete()  # Delete it from DB

    result = await manager.remove(char)
    assert result is False


async def test_remove_updates_fetchall(manager, char1, char2):
    """Test remove updates future fetchall results."""
    await manager.register(char1)
    await manager.register(char2)

    await manager.remove(char1)

    chars = await manager.fetchall(1, 1)
    assert len(chars) == 1
    assert chars[0].name == "Bob"


# FETCHONE TESTS


async def test_fetchone_vchar_passthrough(manager, char1):
    """Test fetchone returns VChar object unchanged."""
    guild = mock_guild(1)
    user = mock_member(1, 1)

    result = await manager.fetchone(guild, user, char1)
    assert result is char1


async def test_fetchone_no_characters_error(manager):
    """Test fetchone raises error when user has no characters."""
    guild = mock_guild(1)
    user = mock_member(999, 1)

    with pytest.raises(CharacterNotFoundError, match="You have no characters"):
        await manager.fetchone(guild, user, None)


async def test_fetchone_multiple_characters_error(manager, char1, char2):
    """Test fetchone raises error when multiple characters and no name given."""
    await manager.register(char1)
    await manager.register(char2)

    guild = mock_guild(1)
    user = mock_member(1, 1)

    with pytest.raises(UnspecifiedCharacterError, match="You have 2 characters"):
        await manager.fetchone(guild, user, None)


async def test_fetchone_single_character_auto_select(manager, char1):
    """Test fetchone auto-selects when user has only one character."""
    await manager.register(char1)

    guild = mock_guild(1)
    user = mock_member(1, 1)

    char = await manager.fetchone(guild, user, None)
    assert char.name == "Alice"


async def test_fetchone_by_name(manager, char1, char2):
    """Test fetchone finds character by name."""
    await manager.register(char1)
    await manager.register(char2)

    guild = mock_guild(1)
    user = mock_member(1, 1)

    char = await manager.fetchone(guild, user, "Bob")
    assert char.name == "Bob"


async def test_fetchone_case_insensitive(manager, char1):
    """Test fetchone name matching is case-insensitive."""
    await manager.register(char1)

    guild = mock_guild(1)
    user = mock_member(1, 1)

    char = await manager.fetchone(guild, user, "alice")
    assert char.name == "Alice"


# TRANSFER TESTS


async def test_transfer_updates_character_user(manager, char1):
    """Test transfer updates character's user ID."""
    await manager.register(char1)

    current_owner = mock_member(1, 1)
    new_owner = mock_member(2, 1)

    await manager.transfer(char1, current_owner, new_owner)

    assert char1.user == 2


async def test_transfer_persists_to_database(manager, char1):
    """Test transfer saves changes to database."""
    await manager.register(char1)

    current_owner = mock_member(1, 1)
    new_owner = mock_member(2, 1)

    await manager.transfer(char1, current_owner, new_owner)

    # Verify in database by fetching for new owner
    chars = await manager.fetchall(1, 2)
    assert len(chars) == 1
    assert chars[0].name == "Alice"


# MARK_INACTIVE/MARK_ACTIVE TESTS


async def test_mark_inactive_sets_timestamp(manager, char1):
    """Test mark_inactive sets 'left' timestamp."""
    await manager.register(char1)

    player = mock_member(1, 1)
    await manager.mark_inactive(player)

    # Reload from database
    reloaded = await VChar.get(char1.id)
    assert "left" in reloaded.stat_log
    assert reloaded.stat_log["left"] is not None


async def test_mark_inactive_handles_multiple_characters(manager, char1, char2):
    """Test mark_inactive handles user with multiple characters."""
    await manager.register(char1)
    await manager.register(char2)

    player = mock_member(1, 1)
    await manager.mark_inactive(player)

    # Both should have timestamp
    for char_id in [char1.id, char2.id]:
        reloaded = await VChar.get(char_id)
        assert "left" in reloaded.stat_log


async def test_mark_active_clears_timestamp(manager, char1):
    """Test mark_active clears 'left' timestamp."""
    await manager.register(char1)

    player = mock_member(1, 1)
    await manager.mark_inactive(player)
    await manager.mark_active(player)

    # Reload from database
    reloaded = await VChar.get(char1.id)
    assert "left" not in reloaded.stat_log


async def test_mark_active_handles_multiple_characters(manager, char1, char2):
    """Test mark_active handles user with multiple characters."""
    await manager.register(char1)
    await manager.register(char2)

    player = mock_member(1, 1)
    await manager.mark_inactive(player)
    await manager.mark_active(player)

    # Both should have timestamp cleared
    for char_id in [char1.id, char2.id]:
        reloaded = await VChar.get(char_id)
        assert "left" not in reloaded.stat_log


# ID_FETCH TESTS


async def test_id_fetch_returns_character(manager, char1):
    """Test id_fetch returns character by ID."""
    await manager.register(char1)

    result = await manager.id_fetch(char1.id)
    assert result is not None
    assert result.name == "Alice"


async def test_id_fetch_returns_none_when_not_found(manager):
    """Test id_fetch returns None for non-existent ID."""
    from beanie import PydanticObjectId

    fake_id = PydanticObjectId()
    result = await manager.id_fetch(fake_id)
    assert result is None
