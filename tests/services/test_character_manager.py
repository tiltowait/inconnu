"""Tests for services.characters.CharacterManager."""

from typing import AsyncGenerator, Generator, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from discord import Guild, Member
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

from db import init_beanie
from errors import (
    CharacterNotFoundError,
    DuplicateCharacterError,
    UnspecifiedCharacterError,
    WrongGuild,
    WrongOwner,
)
from models import VChar
from services import CharacterManager
from tests.characters import gen_char

VCHAR_SAVE = "models.vchar.VChar.save"


@pytest.fixture(autouse=True, scope="module")
def patch_spc_owner():
    with patch.object(VChar, "SPC_OWNER", 999):
        yield


@pytest.fixture(autouse=True, scope="function")
async def beanie_fixture():
    """Configures a mock beanie client for all tests."""
    import db as database

    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    mock_db = client.test
    await init_beanie(mock_db, document_models=database.models())


# Factories


def make_guild(id: int, name: str) -> MagicMock:
    """Create a Guild mock."""
    guild = MagicMock(spec=Guild)
    guild.id = id
    guild.name = name

    return guild


def make_member(id: int, guild: Guild, is_admin: bool) -> Member:
    """Make a Member mock."""
    member = MagicMock(spec=Member)
    member.guild = guild
    member.id = id
    member.top_role.permissions.administrator = is_admin
    member.guild_permissions.administrator = is_admin

    return member


# Guild & Member mocks
# Member names are u (user) num (Guild) num (ID)
# So u12 is on guild 1, with id 2


@pytest.fixture
def g1() -> Guild:
    """A Guild with ID 1."""
    return make_guild(1, "Test Guild")


@pytest.fixture
def u11(g1: Guild) -> Member:
    """A member on g1 with admin permissions."""
    return make_member(1, g1, True)


@pytest.fixture
def u12(g1: Guild) -> Member:
    """A member on g1 WITHOUT admin permissions."""
    return make_member(2, g1, False)


@pytest.fixture
def g2() -> Guild:
    """A Guild with ID 2."""
    return make_guild(2, "Second Guild")


@pytest.fixture
def u21(g2: Guild) -> Member:
    """A member on g2 with admin permissions."""
    return make_member(1, g2, True)


# Character mocks


@pytest.fixture
def c111(g1: Guild, u11: Member) -> VChar:
    """A VChar belonging to u11. Unsaved."""
    char = gen_char("vampire")
    char.name = "Nadea Theron"
    char.guild = g1.id
    char.user = u11.id

    return char


@pytest.fixture
def c112(g1: Guild, u11: Member) -> VChar:
    """A VChar belonging to u11. Unsaved."""
    char = gen_char("vampire")
    char.name = "Jimmy Maxwell"
    char.guild = g1.id
    char.user = u11.id

    return char


@pytest.fixture
def c121(g1: Guild, u12: Member) -> VChar:
    """A VChar belonging to u12. Unsaved."""
    char = gen_char("vampire")
    char.name = "John Wilcox"
    char.guild = g1.id
    char.user = u12.id

    return char


@pytest.fixture
def c211(g2: Guild, u21: Member) -> VChar:
    """A VChar belonging to u21. Unsaved."""
    char = gen_char("vampire")
    char.name = "Victoria Ransom"
    char.guild = g2.id
    char.user = u21.id

    return char


@pytest.fixture
def spc11(g1: Guild) -> VChar:
    char = gen_char("vampire")
    char.name = "Quentin"
    char.guild = g1.id
    char.user = VChar.SPC_OWNER

    return char


# CharacterManager mocks


@pytest.fixture
def mgre() -> CharacterManager:
    """An uninitialized character manager."""
    return CharacterManager()


@pytest.fixture
async def mgrf(
    mgre: CharacterManager,
    c111: VChar,
    c112: VChar,
    c121: VChar,
    c211: VChar,
    spc11: VChar,
) -> CharacterManager:
    """An initialized CharacterManager."""
    await mgre.register(c111)
    await mgre.register(c112)
    await mgre.register(c121)
    await mgre.register(c211)
    await mgre.register(spc11)
    return mgre


@pytest.fixture
async def wrapped_initialize(mgre: CharacterManager) -> AsyncGenerator[AsyncMock, None]:
    """CharacterManager.initialize(), wrapped to test for awaits."""
    with patch(
        "services.CharacterManager.initialize",
        new_callable=AsyncMock,
        wraps=mgre.initialize,
    ) as mock:
        yield mock


@pytest.fixture
def wrapped_find_all() -> Generator[AsyncMock, None]:
    """Wrapped VChar.find_all()."""
    with patch("models.vchar.VChar.find_all", new_callable=Mock, wraps=VChar.find_all) as mock:
        yield mock


# Tests


async def test_initializes(mgrf: CharacterManager):
    await mgrf.initialize()
    assert mgrf.initialized is True
    assert len(mgrf._characters) > 1
    assert len(mgrf._id_cache) > 1


async def test_empty_fetchall(
    wrapped_initialize: AsyncMock,
    wrapped_find_all: AsyncMock,
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
):
    chars = await mgre.fetchall(g1.id, u11.id)
    assert not chars
    wrapped_initialize.assert_awaited_once()
    wrapped_find_all.assert_called_once()

    # Ensure the func works with Discord types as well as ints
    chars = await mgre.fetchall(g1, u11)
    assert not chars
    assert wrapped_initialize.await_count == 2
    wrapped_find_all.assert_called_once()


async def test_fetchall_single(mgre: CharacterManager, g1: Guild, u11: Member, c111: VChar):
    """Test fetchall returns single character."""
    await mgre.register(c111)
    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 1
    assert chars[0].name == c111.name


async def test_fetchall_multiple_sorted(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    c111: VChar,
    c112: VChar,
):
    """Test fetchall returns characters in alphabetical order."""
    # Register Bob before Alice to verify sorting happens
    await mgre.register(c112)  # Jimmy Maxwell
    await mgre.register(c111)  # Nadea Theron

    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 2
    assert chars[0].name == c112.name  # Jimmy comes first alphabetically
    assert chars[1].name == c111.name  # Nadea comes second


async def test_fetchall_filters_by_guild(
    mgre: CharacterManager,
    g1: Guild,
    g2: Guild,
    u11: Member,
    c111: VChar,
):
    """Test fetchall only returns characters from specified guild."""
    await mgre.register(c111)

    # Query different guild with same user ID
    chars = await mgre.fetchall(g2, u11)
    assert len(chars) == 0


async def test_fetchall_filters_by_user(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    u12: Member,
    c111: VChar,
    c121: VChar,
):
    """Test fetchall only returns characters from specified user."""
    await mgre.register(c111)  # u11's character
    await mgre.register(c121)  # u12's character

    # Query for u11 only
    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 1
    assert chars[0].name == c111.name


@pytest.mark.parametrize("name", [None, "Nadea Theron"])
async def test_empty_fetchone_raises(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    name: str | None,
):
    with pytest.raises(CharacterNotFoundError):
        _ = await mgre.fetchone(g1, u11, name)


async def test_register_populates(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    c111: VChar,
    c112: VChar,
):
    await mgre.register(c111)
    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 1
    assert chars[0].name == c111.name

    await mgre.register(c112)
    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 2
    assert chars[0].name == c112.name, "Should have sorted"
    assert chars[1].name == c111.name, "Should have sorted"


async def test_register_duplicate(mgre: CharacterManager, c111: VChar):
    await mgre.register(c111)
    with pytest.raises(DuplicateCharacterError):
        await mgre.register(c111)


async def test_register_inserts_in_middle(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    c111: VChar,
    c112: VChar,
):
    """Test register maintains sorted order when inserting in middle of list."""
    # Register Jimmy and Nadea first
    await mgre.register(c112)  # Jimmy Maxwell
    await mgre.register(c111)  # Nadea Theron

    # Create Kim (alphabetically between Jimmy and Nadea)
    from tests.characters import gen_char

    kim = gen_char("vampire")
    kim.name = "Kim Lee"
    kim.guild = g1.id
    kim.user = u11.id
    await mgre.register(kim)

    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 3
    assert chars[0].name == c112.name  # Jimmy
    assert chars[1].name == kim.name  # Kim (inserted in middle)
    assert chars[2].name == c111.name  # Nadea


async def test_cold_start_populates(
    mgre: CharacterManager,
    g1: Guild,
    u11: Member,
    c111: VChar,
    c112: VChar,
):
    await c111.save()
    await c112.save()

    chars = await mgre.fetchall(g1, u11)
    assert len(chars) == 2
    assert chars[0].name == c112.name, "Should have sorted"
    assert chars[1].name == c111.name, "Should have sorted"


@pytest.mark.parametrize("name", ["Nadea Theron", "nadea theron", None])
async def test_fetchone_single_char_return(
    g1: Guild,
    u11: Member,
    mgre: CharacterManager,
    c111: VChar,
    name: str | None,
):
    await mgre.register(c111)
    char = await mgre.fetchone(g1, u11, name)
    assert char.id == c111.id
    assert char.name == c111.name


async def test_fetchone_multichar_none_raises(
    g1: Guild,
    u11: Member,
    mgrf: CharacterManager,
):
    with pytest.raises(UnspecifiedCharacterError):
        _ = await mgrf.fetchone(g1, u11, None)


async def test_fetchone_multichar_unknown(
    g1: Guild,
    u11: Member,
    mgrf: CharacterManager,
):
    with pytest.raises(CharacterNotFoundError):
        _ = await mgrf.fetchone(g1, u11, "Miss Frizzle")


async def test_fetchone_multichar_name(
    g1: Guild,
    u11: Member,
    mgrf: CharacterManager,
    c111: VChar,
    c112: VChar,
):
    for c in [c111, c112]:
        char = await mgrf.fetchone(g1, u11, c.name.lower())
        assert char.id == c.id
        assert char.name == c.name


async def test_fetchone_vchar_early_return(
    g1: Guild,
    u11: Member,
    mgrf: CharacterManager,
    c111: VChar,
):
    with patch.object(mgrf, "fetchall", new_callable=AsyncMock) as mock_fetchall:
        char = await mgrf.fetchone(g1, u11, c111)
        assert char.id == c111.id
        assert char.name == c111.name
        mock_fetchall.assert_not_awaited()


async def test_id_fetch(mgrf: CharacterManager, c211: VChar):
    char = await mgrf.id_fetch(c211.id_str)
    assert char is not None
    assert char.id == c211.id
    assert char.name == c211.name


async def test_id_fetch_fail(mgrf: CharacterManager):
    char = await mgrf.id_fetch("fake")
    assert char is None


async def test_character_count(g1: Guild, u11: Member, mgrf: CharacterManager):
    count = await mgrf.character_count(g1, u11)
    assert count == 2


async def test_character_count_zero(g1: Guild, u11: Member, mgre: CharacterManager):
    count = await mgre.character_count(g1, u11)
    assert count == 0


async def test_character_count_user_isolation(g1: Guild, u12: Member, mgrf: CharacterManager):
    """Verify character_count only counts the specified user's characters."""
    # u12 has 1 character (c121), u11 has 2 characters (c111, c112)
    count = await mgrf.character_count(g1, u12)
    assert count == 1, "Should only count u12's characters, not u11's"


async def test_character_count_guild_isolation(g2: Guild, u21: Member, mgrf: CharacterManager):
    """Verify character_count only counts characters in the specified guild."""
    # u21 has 1 character on g2 (c211), u11 has 2 characters on g1
    count = await mgrf.character_count(g2, u21)
    assert count == 1, "Should only count g2's characters, not g1's"


async def test_remove(g1: Guild, u11: Member, mgrf: CharacterManager, c111: VChar):
    with patch(
        "models.vchar.VChar.delete", new_callable=AsyncMock, wraps=c111.delete
    ) as mock_delete:
        deleted = await mgrf.remove(c111)
        assert deleted is True
        mock_delete.assert_awaited_once()

        char = await mgrf.id_fetch(c111.id_str)
        assert char is None

        with pytest.raises(CharacterNotFoundError):
            _ = await mgrf.fetchone(g1, u11, c111.name)

        count = await mgrf.character_count(g1.id, u11.id)
        assert count == 1


async def test_remove_fail(mgre: CharacterManager, c111: VChar):
    deleted = await mgre.remove(c111)
    assert not deleted


async def test_mark_inactive(
    mgrf: CharacterManager,
    g1: Guild,
    u11: Member,
):
    with patch("models.vchar.VChar.save", new_callable=AsyncMock) as mock_save:
        await mgrf.mark_inactive(u11)
        assert mock_save.await_count == 2
        chars = await mgrf.fetchall(g1, u11)
        assert len(chars) == 2

        for char in chars:
            assert char.stat_log["left"] is not None

        # Extra thoroughness ...
        left_count = len([c for c in mgrf._characters if "left" in c.stat_log])
        assert left_count == len(chars)


async def test_mark_active(
    mgrf: CharacterManager,
    g1: Guild,
    u11: Member,
):
    await mgrf.mark_inactive(u11)

    with patch("models.vchar.VChar.save", new_callable=AsyncMock) as mock_save:
        await mgrf.mark_active(u11)
        assert mock_save.await_count == 2
        chars = await mgrf.fetchall(g1, u11)
        assert len(chars) == 2

        for char in chars:
            assert "left" not in char.stat_log

        # Extra thoroughness ...
        not_left_count = len([c for c in mgrf._characters if "left" not in c.stat_log])
        assert not_left_count == len(mgrf._characters)


async def test_transfer(mgrf: CharacterManager, u11: Member, u12: Member, c111: VChar):
    char = await mgrf.id_fetch(c111.id_str)
    assert char is not None
    await mgrf.transfer(char, u11, u12)

    assert char.user == u12.id
    assert char.guild == u12.guild.id


async def test_transfer_wrong_owner(mgrf: CharacterManager, u11: Member, u12: Member, c111: VChar):
    char = await mgrf.id_fetch(c111.id_str)
    assert char is not None

    with patch(VCHAR_SAVE, new_callable=AsyncMock) as mock_save:
        with pytest.raises(WrongOwner):
            await mgrf.transfer(char, u12, u11)
        mock_save.assert_not_awaited()


async def test_transfer_wrong_guild(mgrf: CharacterManager, u11: Member, u21: Member, c111: VChar):
    char = await mgrf.id_fetch(c111.id_str)
    assert char is not None

    with patch(VCHAR_SAVE, new_callable=AsyncMock) as mock_save:
        with pytest.raises(WrongGuild):
            await mgrf.transfer(char, u11, u21)
        mock_save.assert_not_awaited()


async def test_exists(
    mgrf: CharacterManager,
    g1: Guild,
    g2: Guild,
    u11: Member,
    u12: Member,
    c111: VChar,
    spc11: VChar,
):
    exists = await mgrf.exists(g1, u11, c111.name, False)
    assert exists

    exists = await mgrf.exists(g1, u11, c111.name, True)
    assert not exists

    exists = await mgrf.exists(g1, u12, c111.name, False)
    assert not exists

    exists = await mgrf.exists(g2, u11, c111.name, False)
    assert not exists

    exists = await mgrf.exists(g1, u11, spc11.name, True)
    assert exists

    exists = await mgrf.exists(g1, u11, spc11.name, False)
    assert not exists


async def test_fetchone_admin(
    mgrf: CharacterManager,
    g1: Guild,
    u11: Member,
    u12: Member,
    c121: VChar,
):
    assert u11.top_role.permissions.administrator is True
    assert u11.guild_permissions.administrator is True

    char = await mgrf.fetchone(g1, u11, c121.id_str)
    assert char.name == c121.name
    assert char.user != u11.id
    assert char.user == u12.id


async def test_fetchone_admin_fail(
    mgrf: CharacterManager,
    g1: Guild,
    u12: Member,
    c111: VChar,
):
    assert u12.top_role.permissions.administrator is False
    assert u12.guild_permissions.administrator is False

    with pytest.raises(LookupError):
        _ = await mgrf.fetchone(g1, u12, c111.id_str)


def test_sort_characters(mgrf: CharacterManager):
    mgrf._characters[0].name = "zzzzzzz"
    mgrf.sort_chars()
    assert mgrf._characters[-1].name == "zzzzzzz"


def test_validate_rejects_wrong_guild(mgrf: CharacterManager, g1: Guild, u21: Member, c211: VChar):
    with pytest.raises(LookupError):
        mgrf._validate(g1, u21, c211)
