"""Test services/settings.py functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import services.settings
from ctx import AppCtx
from models import ExpPerms, ResonanceMode, VGuild, VUser

# Test constants
USER_ID = 123
GUILD_ID = 456


# Fixtures


@pytest.fixture
def mock_vuser_fetch():
    """Fixture that patches VUser.get_or_fetch."""
    with patch("services.settings.VUser.get_or_fetch", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_vguild_fetch():
    """Fixture that patches VGuild.get_or_fetch."""
    with patch("services.settings.VGuild.get_or_fetch", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_is_admin():
    """Fixture that patches is_admin."""
    with patch("services.settings.is_admin") as mock:
        yield mock


# Mock factories


def mock_ctx(user_id: int = USER_ID, guild_id: int = GUILD_ID):
    """Create a mock AppCtx."""
    ctx = MagicMock(spec=AppCtx)
    ctx.user.id = user_id
    ctx.guild.id = guild_id
    return ctx


def mock_guild(guild_id: int = GUILD_ID):
    """Create a mock Discord Guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    return guild


def mock_vuser(accessibility: bool = False):
    """Create a mock VUser with settings."""
    vuser = MagicMock(spec=VUser)
    vuser.settings.accessibility = accessibility
    return vuser


def mock_vguild(
    accessibility: bool = False,
    experience_permissions: ExpPerms = ExpPerms.UNRESTRICTED,
    oblivion_stains: list | None = None,
    add_empty_resonance: bool = False,
    resonance: ResonanceMode = ResonanceMode.STANDARD,
    max_hunger: int = 5,
    update_channel: int | None = None,
    changelog_channel: int | None = None,
    deletion_channel: int | None = None,
):
    """Create a mock VGuild with settings."""
    vguild = MagicMock(spec=VGuild)
    vguild.settings.accessibility = accessibility
    vguild.settings.experience_permissions = experience_permissions
    vguild.settings.oblivion_stains = oblivion_stains or []
    vguild.settings.add_empty_resonance = add_empty_resonance
    vguild.settings.resonance = resonance
    vguild.settings.max_hunger = max_hunger
    vguild.settings.update_channel = update_channel
    vguild.settings.changelog_channel = changelog_channel
    vguild.settings.deletion_channel = deletion_channel
    return vguild


# Tests for accessible()


async def test_accessible_user_override_true(mock_vuser_fetch, mock_vguild_fetch):
    """Test that user accessibility=True overrides guild settings."""
    ctx = mock_ctx()
    mock_vuser_fetch.return_value = mock_vuser(accessibility=True)
    mock_vguild_fetch.return_value = mock_vguild(accessibility=False)

    result = await services.settings.accessible(ctx)
    assert result is True


async def test_accessible_user_false_guild_true(mock_vuser_fetch, mock_vguild_fetch):
    """Test that guild accessibility is used when user accessibility is False."""
    ctx = mock_ctx()
    mock_vuser_fetch.return_value = mock_vuser(accessibility=False)
    mock_vguild_fetch.return_value = mock_vguild(accessibility=True)

    result = await services.settings.accessible(ctx)
    assert result is True


async def test_accessible_both_false(mock_vuser_fetch, mock_vguild_fetch):
    """Test that accessible returns False when both user and guild are False."""
    ctx = mock_ctx()
    mock_vuser_fetch.return_value = mock_vuser(accessibility=False)
    mock_vguild_fetch.return_value = mock_vguild(accessibility=False)

    result = await services.settings.accessible(ctx)
    assert result is False


# Tests for can_emoji()


async def test_can_emoji_inverts_accessible(mock_vuser_fetch, mock_vguild_fetch):
    """Test that can_emoji returns the inverse of accessible."""
    ctx = mock_ctx()

    # Test when accessible is True (can_emoji should be False)
    mock_vuser_fetch.return_value = mock_vuser(accessibility=True)
    mock_vguild_fetch.return_value = mock_vguild(accessibility=False)

    result = await services.settings.can_emoji(ctx)
    assert result is False

    # Test when accessible is False (can_emoji should be True)
    mock_vuser_fetch.return_value = mock_vuser(accessibility=False)
    mock_vguild_fetch.return_value = mock_vguild(accessibility=False)

    result = await services.settings.can_emoji(ctx)
    assert result is True


# Tests for can_adjust_current_xp()


async def test_can_adjust_current_xp_admin_always_true(mock_is_admin):
    """Test that admins can always adjust current XP."""
    ctx = mock_ctx()
    mock_is_admin.return_value = True

    result = await services.settings.can_adjust_current_xp(ctx)
    assert result is True


@pytest.mark.parametrize(
    "permission,expected",
    [
        (ExpPerms.UNRESTRICTED, True),
        (ExpPerms.UNSPENT_ONLY, True),
        (ExpPerms.LIFETIME_ONLY, False),
        (ExpPerms.ADMIN_ONLY, False),
    ],
)
async def test_can_adjust_current_xp_non_admin(
    mock_is_admin, mock_vguild_fetch, permission, expected
):
    """Test current XP permissions for non-admins with different guild settings."""
    ctx = mock_ctx()
    mock_is_admin.return_value = False
    mock_vguild_fetch.return_value = mock_vguild(experience_permissions=permission)

    result = await services.settings.can_adjust_current_xp(ctx)
    assert result is expected


# Tests for can_adjust_lifetime_xp()


async def test_can_adjust_lifetime_xp_admin_always_true(mock_is_admin):
    """Test that admins can always adjust lifetime XP."""
    ctx = mock_ctx()
    mock_is_admin.return_value = True

    result = await services.settings.can_adjust_lifetime_xp(ctx)
    assert result is True


@pytest.mark.parametrize(
    "permission,expected",
    [
        (ExpPerms.UNRESTRICTED, True),
        (ExpPerms.UNSPENT_ONLY, False),
        (ExpPerms.LIFETIME_ONLY, True),
        (ExpPerms.ADMIN_ONLY, False),
    ],
)
async def test_can_adjust_lifetime_xp_non_admin(
    mock_is_admin, mock_vguild_fetch, permission, expected
):
    """Test lifetime XP permissions for non-admins with different guild settings."""
    ctx = mock_ctx()
    mock_is_admin.return_value = False
    mock_vguild_fetch.return_value = mock_vguild(experience_permissions=permission)

    result = await services.settings.can_adjust_lifetime_xp(ctx)
    assert result is expected


# Tests for oblivion_stains()


async def test_oblivion_stains_returns_guild_setting(mock_vguild_fetch):
    """Test that oblivion_stains returns the guild's stain list."""
    guild = mock_guild()
    expected_stains = [1, 2, 3]
    mock_vguild_fetch.return_value = mock_vguild(oblivion_stains=expected_stains)

    result = await services.settings.oblivion_stains(guild)
    assert result == expected_stains


# Tests for add_empty_resonance()


@pytest.mark.parametrize("add_empty", [True, False])
async def test_add_empty_resonance(mock_vguild_fetch, add_empty):
    """Test that add_empty_resonance returns the guild setting."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(add_empty_resonance=add_empty)

    result = await services.settings.add_empty_resonance(guild)
    assert result is add_empty


# Tests for resonance_mode()


async def test_resonance_mode_returns_standard_when_guild_none():
    """Test that resonance_mode returns STANDARD when guild is None."""
    result = await services.settings.resonance_mode(None)
    assert result == ResonanceMode.STANDARD


@pytest.mark.parametrize(
    "mode",
    [ResonanceMode.STANDARD, ResonanceMode.TATTERED_FACADE, ResonanceMode.ADD_EMPTY],
)
async def test_resonance_mode_returns_guild_setting(mock_vguild_fetch, mode):
    """Test that resonance_mode returns the guild's resonance mode."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(resonance=mode)

    result = await services.settings.resonance_mode(guild)
    assert result == mode


# Tests for max_hunger()


@pytest.mark.parametrize("hunger", [5, 10, 3])
async def test_max_hunger_returns_guild_setting(mock_vguild_fetch, hunger):
    """Test that max_hunger returns the guild's max hunger setting."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(max_hunger=hunger)

    result = await services.settings.max_hunger(guild)
    assert result == hunger


# Tests for update_channel()


async def test_update_channel_returns_none_when_not_set(mock_vguild_fetch):
    """Test that update_channel returns None when no channel is set."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(update_channel=None)

    result = await services.settings.update_channel(guild)
    assert result is None


async def test_update_channel_returns_channel_when_set(mock_vguild_fetch):
    """Test that update_channel returns the channel object when set."""
    guild = mock_guild()
    channel_id = 789
    mock_channel = MagicMock(spec=discord.TextChannel)
    guild.get_channel.return_value = mock_channel
    mock_vguild_fetch.return_value = mock_vguild(update_channel=channel_id)

    result = await services.settings.update_channel(guild)
    assert result == mock_channel
    guild.get_channel.assert_called_once_with(channel_id)


# Tests for changelog_channel()


async def test_changelog_channel_returns_none_when_not_set(mock_vguild_fetch):
    """Test that changelog_channel returns None when no channel is set."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(changelog_channel=None)

    result = await services.settings.changelog_channel(guild)
    assert result is None


async def test_changelog_channel_returns_id_when_set(mock_vguild_fetch):
    """Test that changelog_channel returns the channel ID when set."""
    guild = mock_guild()
    channel_id = 890
    mock_vguild_fetch.return_value = mock_vguild(changelog_channel=channel_id)

    result = await services.settings.changelog_channel(guild)
    assert result == channel_id


# Tests for deletion_channel()


async def test_deletion_channel_returns_none_when_not_set(mock_vguild_fetch):
    """Test that deletion_channel returns None when no channel is set."""
    guild = mock_guild()
    mock_vguild_fetch.return_value = mock_vguild(deletion_channel=None)

    result = await services.settings.deletion_channel(guild)
    assert result is None


async def test_deletion_channel_returns_id_when_set(mock_vguild_fetch):
    """Test that deletion_channel returns the channel ID when set."""
    guild = mock_guild()
    channel_id = 901
    mock_vguild_fetch.return_value = mock_vguild(deletion_channel=channel_id)

    result = await services.settings.deletion_channel(guild)
    assert result == channel_id
