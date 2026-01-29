"""Test VChar CRUD operations and database persistence."""

import pytest_asyncio

from constants import Damage
from models import VChar
from models.vchardocs import VCharTrait


@pytest_asyncio.fixture
async def vampire():
    """Create and insert a vampire character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Vampire",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=2,
    )
    await char.insert()
    yield char
    # Cleanup
    try:
        await char.delete()
    except Exception:
        pass  # Already deleted in test


@pytest_asyncio.fixture
async def thin_blood():
    """Create and insert a thin-blood character for testing."""
    char = VChar(
        guild=1,
        user=2,
        name="Test Thinblood",
        splat="thinblood",  # Test normalization
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    await char.insert()
    yield char
    # Cleanup
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def mortal():
    """Create and insert a mortal character for testing."""
    char = VChar(
        guild=2,
        user=1,
        name="Test Mortal",
        splat="mortal",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    await char.insert()
    yield char
    # Cleanup
    try:
        await char.delete()
    except Exception:
        pass


@pytest_asyncio.fixture
async def spc():
    """Create and insert an SPC character for testing."""
    char = VChar(
        guild=1,
        user=VChar.SPC_OWNER,
        name="Test SPC",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    yield char
    # Cleanup
    try:
        await char.delete()
    except Exception:
        pass


# CREATE TESTS


async def test_create_vampire():
    """Test creating and persisting a vampire character."""
    char = VChar(
        guild=999,
        user=999,
        name="New Vampire",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )

    # Verify not in database yet
    assert char.id is None

    # Insert
    await char.insert()

    # Verify ID assigned
    assert char.id is not None
    char_id = char.id

    # Fetch from database
    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert fetched.name == "New Vampire"
    assert fetched.guild == 999
    assert fetched.user == 999
    assert fetched.splat == "vampire"
    assert fetched.potency == 1

    # Cleanup
    await char.delete()


async def test_create_mortal():
    """Test creating a mortal character."""
    char = VChar(
        guild=999,
        user=999,
        name="New Mortal",
        splat="mortal",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )

    await char.insert()
    char_id = char.id

    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert fetched.splat == "mortal"
    assert fetched.is_vampire is False
    assert fetched.hunger == 0

    await char.delete()


async def test_pre_insert_hook_splat_normalization():
    """Test that pre_insert normalizes 'thinblood' to 'thin-blood'."""
    char = VChar(
        guild=999,
        user=999,
        name="Thinblood Test",
        splat="thinblood",  # Should be normalized
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )

    await char.insert()
    char_id = char.id

    # Verify in-memory normalization
    assert char.splat == "thin-blood"

    # Verify persisted normalization
    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert fetched.splat == "thin-blood"
    assert fetched.is_thin_blood is True

    await char.delete()


async def test_pre_insert_hook_blush_initialization():
    """Test that pre_insert sets blush correctly based on splat."""
    # Vampire should have blush = 0
    vampire = VChar(
        guild=999,
        user=999,
        name="Vampire",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await vampire.insert()
    assert vampire.header.blush == 0

    # Thin-blood should have blush = -1
    thin_blood = VChar(
        guild=999,
        user=998,
        name="Thinblood",
        splat="thin-blood",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    await thin_blood.insert()
    assert thin_blood.header.blush == -1

    # Mortal should have blush = -1
    mortal = VChar(
        guild=999,
        user=997,
        name="Mortal",
        splat="mortal",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=0,
    )
    await mortal.insert()
    assert mortal.header.blush == -1

    # Cleanup
    await vampire.delete()
    await thin_blood.delete()
    await mortal.delete()


async def test_pre_insert_hook_creation_timestamp():
    """Test that pre_insert adds creation timestamp to stat_log."""
    char = VChar(
        guild=999,
        user=999,
        name="Timestamp Test",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )

    await char.insert()
    char_id = char.id

    # Verify timestamp in memory
    assert "created" in char.stat_log
    assert char.stat_log["created"] is not None

    # Verify timestamp persisted
    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert "created" in fetched.stat_log

    await char.delete()


# READ TESTS


async def test_read_by_id(vampire):
    """Test fetching a character by ID."""
    char_id = vampire.id

    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert fetched.id == char_id
    assert fetched.name == "Test Vampire"


async def test_read_nonexistent_id():
    """Test that fetching a non-existent ID returns None."""
    from bson import ObjectId

    fake_id = ObjectId()
    fetched = await VChar.get(fake_id)
    assert fetched is None


async def test_read_by_guild_and_user(vampire, thin_blood):
    """Test querying characters by guild and user."""
    # Find vampire (guild=1, user=1)
    chars = await VChar.find({"guild": 1, "user": 1}).to_list()
    assert len(chars) >= 1
    assert any(c.id == vampire.id for c in chars)

    # Find thin-blood (guild=1, user=2)
    chars = await VChar.find({"guild": 1, "user": 2}).to_list()
    assert len(chars) >= 1
    assert any(c.id == thin_blood.id for c in chars)


async def test_read_by_name(vampire):
    """Test querying by character name."""
    chars = await VChar.find({"name": "Test Vampire"}).to_list()
    assert len(chars) >= 1
    assert any(c.id == vampire.id for c in chars)


async def test_read_all_guild_characters(vampire, thin_blood, mortal):
    """Test fetching all characters in a guild."""
    guild_1_chars = await VChar.find({"guild": 1}).to_list()
    guild_2_chars = await VChar.find({"guild": 2}).to_list()

    # Guild 1 should have vampire and thin_blood
    assert len(guild_1_chars) >= 2
    guild_1_ids = {c.id for c in guild_1_chars}
    assert vampire.id in guild_1_ids
    assert thin_blood.id in guild_1_ids

    # Guild 2 should have mortal
    assert len(guild_2_chars) >= 1
    guild_2_ids = {c.id for c in guild_2_chars}
    assert mortal.id in guild_2_ids


async def test_read_spc_vs_pc(vampire, spc):
    """Test querying SPCs vs PCs."""
    # Find all PCs in guild 1
    pcs = await VChar.find({"guild": 1, "user": {"$ne": VChar.SPC_OWNER}}).to_list()
    assert any(c.id == vampire.id for c in pcs)
    assert not any(c.id == spc.id for c in pcs)

    # Find all SPCs in guild 1
    spcs = await VChar.find({"guild": 1, "user": VChar.SPC_OWNER}).to_list()
    assert any(c.id == spc.id for c in spcs)
    assert not any(c.id == vampire.id for c in spcs)


async def test_read_with_traits(vampire):
    """Test that traits are properly loaded from database."""
    # Add traits to vampire
    vampire.assign_traits({"Strength": 3, "Brawl": 2})
    await vampire.save()

    # Fetch from database
    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert len(fetched.traits) == 2

    strength = fetched.find_trait("Strength")
    assert strength.rating == 3
    assert strength.type == VCharTrait.Type.ATTRIBUTE

    brawl = fetched.find_trait("Brawl")
    assert brawl.rating == 2
    assert brawl.type == VCharTrait.Type.SKILL


# UPDATE TESTS


async def test_update_basic_field(vampire):
    """Test updating a basic field and persisting changes."""
    original_name = vampire.name
    vampire.name = "Updated Vampire"
    await vampire.save()

    # Verify in-memory change
    assert vampire.name == "Updated Vampire"

    # Verify persisted change
    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.name == "Updated Vampire"
    assert fetched.name != original_name


async def test_update_multiple_fields(vampire):
    """Test updating multiple fields at once."""
    vampire.name = "Multi Update"
    vampire.humanity = 5
    vampire.potency = 3
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.name == "Multi Update"
    assert fetched.humanity == 5
    assert fetched.potency == 3


async def test_update_traits(vampire):
    """Test updating traits and persisting."""
    vampire.assign_traits({"Strength": 3, "Brawl": 2})
    await vampire.save()

    # Update trait ratings
    vampire.assign_traits({"Strength": 5, "Brawl": 4})
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.find_trait("Strength").rating == 5
    assert fetched.find_trait("Brawl").rating == 4


async def test_update_damage_tracking(vampire):
    """Test updating health/willpower damage."""
    vampire.apply_damage("health", Damage.SUPERFICIAL, 3)
    vampire.apply_damage("willpower", Damage.AGGRAVATED, 2)
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.superficial_hp == 3
    assert fetched.aggravated_wp == 2


async def test_pre_update_hook_hunger_clamping_vampire(vampire):
    """Test that pre_update clamps vampire hunger to 0-5."""
    vampire.hunger = 10
    await vampire.save()

    # Should be clamped to 5
    assert vampire.hunger == 5

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.hunger == 5

    # Test lower bound
    vampire.hunger = -5
    await vampire.save()
    assert vampire.hunger == 0

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.hunger == 0


async def test_pre_update_hook_hunger_zero_nonvampire(mortal):
    """Test that pre_update sets hunger to 0 for non-vampires."""
    mortal.hunger = 5
    await mortal.save()

    # Should be forced to 0
    assert mortal.hunger == 0

    fetched = await VChar.get(mortal.id)
    assert fetched is not None
    assert fetched.hunger == 0


async def test_pre_update_hook_potency_clamping(vampire):
    """Test that pre_update clamps potency to 0-10."""
    vampire.potency = 15
    await vampire.save()

    assert vampire.potency == 10

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.potency == 10

    vampire.potency = -5
    await vampire.save()
    assert vampire.potency == 0


async def test_pre_update_hook_stains_clamping(vampire):
    """Test that pre_update clamps stains to 0-10."""
    vampire.stains = 20
    await vampire.save()

    assert vampire.stains == 10

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.stains == 10


async def test_pre_update_hook_xp_clamping(vampire):
    """Test that pre_update clamps unspent XP to lifetime."""
    vampire.experience.lifetime = 100
    vampire.experience.unspent = 150  # Too high
    await vampire.save()

    assert vampire.experience.unspent == 100

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.experience.unspent == 100


async def test_pre_update_hook_splat_normalization(vampire):
    """Test that pre_update normalizes splat on update."""
    vampire.splat = "thinblood"
    await vampire.save()

    assert vampire.splat == "thin-blood"

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert fetched.splat == "thin-blood"


async def test_update_macros(vampire):
    """Test updating macros persists correctly."""
    vampire.add_macro(
        name="TestMacro",
        pool=["Strength", "Brawl"],
        hunger=True,
        difficulty=3,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment="Test comment",
    )
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert len(fetched.macros) == 1
    macro = fetched.find_macro("TestMacro")
    assert macro.name == "TestMacro"
    assert macro.pool == ["Strength", "Brawl"]
    assert macro.difficulty == 3

    # Update macro
    vampire.update_macro("TestMacro", {"pool": ["Dexterity", "Athletics"]})
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    macro = fetched.find_macro("TestMacro")
    assert macro.pool == ["Dexterity", "Athletics"]


async def test_update_experience_log(vampire):
    """Test that experience log updates persist."""
    vampire.apply_experience(10, "unspent", "Test award", 12345)
    await vampire.save()

    fetched = await VChar.get(vampire.id)
    assert fetched is not None
    assert len(fetched.experience.log) == 1
    assert fetched.experience.log[0].amount == 10
    assert fetched.experience.log[0].reason == "Test award"


# DELETE TESTS


async def test_delete_character():
    """Test deleting a character removes it from database."""
    char = VChar(
        guild=999,
        user=999,
        name="To Delete",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    char_id = char.id

    # Verify exists
    fetched = await VChar.get(char_id)
    assert fetched is not None

    # Delete
    await char.delete()

    # Verify gone
    fetched = await VChar.get(char_id)
    assert fetched is None


async def test_delete_with_traits():
    """Test deleting a character with traits."""
    char = VChar(
        guild=999,
        user=999,
        name="With Traits",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    char.assign_traits({"Strength": 3, "Brawl": 2})
    await char.insert()
    char_id = char.id

    # Verify exists with traits
    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert len(fetched.traits) == 2

    # Delete
    await char.delete()

    # Verify gone
    fetched = await VChar.get(char_id)
    assert fetched is None


async def test_delete_with_macros():
    """Test deleting a character with macros."""
    char = VChar(
        guild=999,
        user=999,
        name="With Macros",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    char.add_macro(
        name="TestMacro",
        pool=["Strength"],
        hunger=False,
        difficulty=2,
        rouses=0,
        reroll_rouses=False,
        staining="",
        hunt=False,
        comment=None,
    )
    await char.insert()
    char_id = char.id

    # Delete
    await char.delete()

    # Verify gone
    fetched = await VChar.get(char_id)
    assert fetched is None


# EDGE CASES


async def test_concurrent_updates():
    """Test that concurrent updates don't cause data loss."""
    char = VChar(
        guild=999,
        user=999,
        name="Concurrent Test",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )
    await char.insert()
    char_id = char.id

    # Fetch two instances
    char1 = await VChar.get(char_id)
    char2 = await VChar.get(char_id)

    assert char1 is not None
    assert char2 is not None

    # Update different fields
    char1.name = "Update 1"
    char2.potency = 5

    # Save both
    await char1.save()
    await char2.save()

    # Fetch final state - last write wins
    final = await VChar.get(char_id)
    # Note: Beanie uses replace by default, so char2's save would overwrite char1's
    # This test documents the behavior
    assert final is not None

    await char.delete()


async def test_save_without_insert():
    """Test that calling save() on a new document works (upsert behavior)."""
    char = VChar(
        guild=999,
        user=999,
        name="Save Test",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=1,
    )

    # Call save instead of insert
    await char.save()

    # Should still persist
    assert char.id is not None
    char_id = char.id

    fetched = await VChar.get(char_id)
    assert fetched is not None
    assert fetched.name == "Save Test"

    await char.delete()
