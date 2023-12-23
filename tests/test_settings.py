"""Test bot settings."""

from dataclasses import dataclass
from random import randint
from types import SimpleNamespace as SN

import pytest

import inconnu
from inconnu import VGuild, VUser
from inconnu.settings.guildsettings import ExpPerms, VGuildSettings


@dataclass
class Channel:
    id: int

    def permissions_for(self, _):
        return SN(external_emojis=True)

    @property
    def mention(self) -> str:
        return f"<#{self.id}>"

    def __eq__(self, o):
        return self.id == o.id


@dataclass
class Guild:
    id: int
    name: str
    default_role = None

    def get_channel(self, channel_id):
        return Channel(id=channel_id)


@dataclass
class User:
    id: int
    guild_permissions = SN(administrator=True)


@dataclass
class Context:
    guild: Guild
    channel: Channel
    user: User


@pytest.fixture
def uid() -> int:
    return randint(1, 100000)


@pytest.fixture
def uid2() -> int:
    return randint(1, 100000)


@pytest.fixture
def uid3() -> int:
    return randint(1, 100000)


@pytest.fixture
def guild(uid):
    """A Discord guild."""
    return Guild(id=uid, name="Test")


@pytest.fixture
def channel(uid2):
    """A Discord channel."""
    return Channel(id=uid2)


@pytest.fixture
def user(uid3):
    """A Discord user."""
    return User(id=uid3)


@pytest.fixture
def ctx(guild, channel, user):
    return Context(guild=guild, channel=channel, user=user)


async def test_find_user_creates_user(uid):
    assert await VUser.find_one(VUser.user == uid) is None

    user = await inconnu.settings.find_user(uid)
    assert isinstance(user, VUser)
    assert user.user == uid

    found = await VUser.find_one(VUser.user == uid)
    assert user.id == found.id
    assert user.user == found.user


async def test_find_user_creates_only_one_user(uid):
    for _ in range(10):
        user = await inconnu.settings.find_user(uid)
        assert user is not None

    assert await VUser.count() == 1


def test_vguild_settings_oblivion_stains_unique():
    v1 = VGuildSettings()
    v2 = VGuildSettings()

    assert id(v1) != id(v2), "oblivion_stains lists are shared across instances"


async def test_guild_joined(guild):
    await inconnu.stats.guild_joined(guild)
    g = await VGuild.find_one(VGuild.guild == guild.id)

    assert g is not None
    assert g.guild == guild.id
    assert g.active
    assert g.left is None


async def test_guild_left(guild):
    await inconnu.stats.guild_joined(guild)
    await inconnu.stats.guild_left(guild)

    g = await VGuild.find_one(VGuild.guild == guild.id)
    assert g is not None
    assert g.guild == guild.id
    assert not g.active
    assert g.left is not None


@pytest.mark.parametrize("enabled", [True, False])
async def test_accessibility_user(enabled: bool, ctx: Context):
    user = await inconnu.settings.find_user(ctx.user)
    user.settings.accessibility = enabled

    guild = await inconnu.settings.find_guild(ctx.guild)
    assert guild.settings.accessibility is False

    assert await inconnu.settings.accessible(ctx) == enabled


@pytest.mark.parametrize("enabled", [True, False])
async def test_accessibility_guild(enabled: bool, ctx: Context):
    guild = await inconnu.settings.find_guild(ctx.guild)
    guild.settings.accessibility = enabled

    user = await inconnu.settings.find_user(ctx.user)
    assert user.settings.accessibility is False

    assert await inconnu.settings.accessible(ctx) == enabled


async def test_accessibility_fallback(ctx: Context):
    ctx.channel.permissions_for = lambda _: SN(external_emojis=False)
    assert await inconnu.settings.accessible(ctx) is True


async def test_set_accessibility(ctx: Context):
    assert await inconnu.settings.accessible(ctx) is False
    await inconnu.settings.set_accessibility(ctx, True, "guild")
    assert await inconnu.settings.accessible(ctx) is True


@pytest.mark.parametrize(
    "value,expected",
    [
        (100, [1, 10]),
        (0, []),
        (1, [1]),
        (10, [10]),
    ],
)
async def test_set_oblivion_stains(value: int, expected: list[int], ctx: Context):
    assert await inconnu.settings.oblivion_stains(ctx.guild) == [1, 10]
    await inconnu.settings.set_oblivion_stains(ctx, value)
    assert await inconnu.settings.oblivion_stains(ctx.guild) == expected


async def test_add_empty_resonance(ctx: Context):
    assert await inconnu.settings.add_empty_resonance(ctx.guild) is False
    await inconnu.settings.set_empty_resonance(ctx, True)
    assert await inconnu.settings.add_empty_resonance(ctx.guild) is True


async def test_set_max_hunger(ctx: Context):
    assert await inconnu.settings.max_hunger(ctx.guild) == 5
    await inconnu.settings.set_max_hunger(ctx, 10)
    assert await inconnu.settings.max_hunger(ctx.guild) == 10


@pytest.mark.parametrize(
    "perms,unspent,lifetime,admin",
    [
        (ExpPerms.UNSPENT_ONLY, True, False, False),
        (ExpPerms.UNSPENT_ONLY, True, True, True),
        (ExpPerms.LIFETIME_ONLY, False, True, False),
        (ExpPerms.LIFETIME_ONLY, True, True, True),
        (ExpPerms.ADMIN_ONLY, False, False, False),
        (ExpPerms.ADMIN_ONLY, True, True, True),
    ],
)
async def test_set_xp_perms(
    perms: ExpPerms, unspent: bool, lifetime: bool, admin: bool, ctx: Context
):
    assert await inconnu.settings.can_adjust_current_xp(ctx) is True
    assert await inconnu.settings.can_adjust_lifetime_xp(ctx) is True

    # The context gets reused between tests, so make sure we have admin privileges
    ctx.user.guild_permissions.administrator = True
    await inconnu.settings.set_xp_permissions(ctx, perms)

    # Patch the guild permissions to match admin state
    ctx.user.guild_permissions.administrator = admin

    assert await inconnu.settings.can_adjust_current_xp(ctx) == unspent
    assert await inconnu.settings.can_adjust_lifetime_xp(ctx) == lifetime


async def test_set_update_channel(ctx: Context):
    assert await inconnu.settings.update_channel(ctx.guild) is None
    await inconnu.settings.set_update_channel(ctx, ctx.channel)
    assert await inconnu.settings.update_channel(ctx.guild) == ctx.channel

    # Test unsetting
    await inconnu.settings.set_update_channel(ctx, None)
    assert await inconnu.settings.update_channel(ctx.guild) is None


async def test_set_changelog_channel(ctx: Context):
    assert await inconnu.settings.changelog_channel(ctx.guild) is None
    await inconnu.settings.set_changelog_channel(ctx, ctx.channel)
    assert await inconnu.settings.changelog_channel(ctx.guild) == ctx.channel.id

    # Test unsetting
    await inconnu.settings.set_changelog_channel(ctx, None)
    assert await inconnu.settings.changelog_channel(ctx.guild) is None


async def test_set_deletion_channel(ctx: Context):
    assert await inconnu.settings.deletion_channel(ctx.guild) is None
    await inconnu.settings.set_deletion_channel(ctx, ctx.channel)
    assert await inconnu.settings.deletion_channel(ctx.guild) == ctx.channel.id

    # Test unsetting
    await inconnu.settings.set_deletion_channel(ctx, None)
    assert await inconnu.settings.deletion_channel(ctx.guild) is None
