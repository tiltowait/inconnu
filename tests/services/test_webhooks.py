"""Tests for services/webhooks.py WebhookCache class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from services import WebhookCache
from services.webhooks import ChannelWebhook, webhook_home

type MockChannel = MagicMock
type MockGuild = MagicMock
type MockThread = MagicMock
type MockUser = MagicMock
type MockWebhook = MagicMock

# Fixtures


@pytest.fixture
def bot_id() -> int:
    """Bot user ID for testing."""
    return 12345


@pytest.fixture
def cache(bot_id: int) -> WebhookCache:
    """WebhookCache instance."""
    return WebhookCache(bot_id)


@pytest.fixture
def mock_user(bot_id: int):
    """Mock Discord user (the bot)."""
    user = MagicMock(spec=discord.User)
    user.id = bot_id
    return user


@pytest.fixture
def other_user():
    """Mock Discord user (another bot)."""
    user = MagicMock(spec=discord.User)
    user.id = 99999
    return user


@pytest.fixture
def mock_webhook(mock_user):
    """Mock Discord webhook owned by bot."""
    webhook = MagicMock(spec=discord.Webhook)
    webhook.id = 1001
    webhook.user = mock_user
    webhook.channel_id = 5001
    webhook.name = "Test Webhook"
    webhook.channel = MagicMock(spec=discord.TextChannel)
    webhook.channel.name = "test-channel"
    return webhook


@pytest.fixture
def mock_channel():
    """Mock Discord TextChannel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 5001
    channel.name = "test-channel"
    channel.guild = MagicMock(spec=discord.Guild)
    channel.guild.id = 7001
    channel.guild.name = "Test Guild"
    channel.guild.webhooks = AsyncMock(return_value=[])
    channel.webhooks = AsyncMock(return_value=[])
    channel.create_webhook = AsyncMock()
    return channel


@pytest.fixture
def mock_guild():
    """Mock Discord Guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 7001
    guild.name = "Test Guild"
    guild.webhooks = AsyncMock(return_value=[])
    return guild


# Initialization Tests


def test_init_sets_bot_id(bot_id: int):
    """Test that initialization sets bot_id correctly."""
    cache = WebhookCache(bot_id)
    assert cache.bot_id == bot_id


def test_init_creates_empty_collections(cache: WebhookCache):
    """Test that initialization creates empty data structures."""
    assert cache._webhooks == {}
    assert cache.webhook_ids == set()
    assert cache._guilds_polled == set()


# _check_webhook Tests


async def test_check_webhook_returns_true_when_found(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """_check_webhook finds the webhook by its ID."""
    mock_channel.webhooks.return_value = [mock_webhook]

    result = await cache._check_webhook(mock_channel, mock_webhook.id)

    assert result is True


async def test_check_webhook_returns_false_when_empty(
    cache: WebhookCache, mock_channel: MockChannel
):
    """_check_webhook is False when the channel has no webhooks."""
    mock_channel.webhooks.return_value = []

    result = await cache._check_webhook(mock_channel, 1001)

    assert result is False


async def test_check_webhook_ignores_our_other_webhooks(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """Another of our webhooks in the channel doesn't stand in for the
    missing one."""
    mock_channel.webhooks.return_value = [mock_webhook]

    result = await cache._check_webhook(mock_channel, mock_webhook.id + 1)

    assert result is False


# _poll_guild Tests


async def test_poll_guild_adds_webhooks_to_cache(
    cache: WebhookCache,
    mock_guild,
    mock_webhook,
):
    """Test that _poll_guild adds bot's webhooks to _webhooks dict."""
    mock_guild.webhooks.return_value = [mock_webhook]

    await cache._poll_guild(mock_guild)

    assert mock_webhook.channel_id in cache._webhooks
    assert cache._webhooks[mock_webhook.channel_id] == mock_webhook


async def test_poll_guild_adds_webhook_ids(
    cache: WebhookCache,
    mock_guild,
    mock_webhook,
):
    """Test that _poll_guild adds webhook IDs to webhook_ids set."""
    mock_guild.webhooks.return_value = [mock_webhook]

    await cache._poll_guild(mock_guild)

    assert mock_webhook.id in cache.webhook_ids


async def test_poll_guild_marks_guild_as_polled(
    cache: WebhookCache,
    mock_guild,
    mock_webhook,
):
    """Test that _poll_guild marks guild in _guilds_polled."""
    mock_guild.webhooks.return_value = [mock_webhook]

    await cache._poll_guild(mock_guild)

    assert mock_guild.id in cache._guilds_polled


async def test_poll_guild_ignores_other_bots(
    cache: WebhookCache,
    mock_guild,
    other_user,
):
    """Test that _poll_guild ignores webhooks from other bots."""
    other_webhook = MagicMock(spec=discord.Webhook)
    other_webhook.user = other_user
    other_webhook.channel_id = 5002
    mock_guild.webhooks.return_value = [other_webhook]

    await cache._poll_guild(mock_guild)

    assert other_webhook.channel_id not in cache._webhooks
    assert other_webhook.id not in cache.webhook_ids


async def test_poll_guild_ignores_webhooks_without_channel_id(
    cache: WebhookCache,
    mock_guild,
    mock_user,
):
    """Test that _poll_guild ignores webhooks with channel_id=None."""
    orphaned_webhook = MagicMock(spec=discord.Webhook)
    orphaned_webhook.user = mock_user
    orphaned_webhook.channel_id = None
    orphaned_webhook.id = 9999
    mock_guild.webhooks.return_value = [orphaned_webhook]

    await cache._poll_guild(mock_guild)

    assert None not in cache._webhooks
    assert 9999 not in cache.webhook_ids


async def test_poll_guild_ignores_webhooks_with_user_none(
    cache: WebhookCache,
    mock_guild,
):
    """Test that _poll_guild ignores webhooks where user is None."""
    webhook = MagicMock(spec=discord.Webhook)
    webhook.user = None
    webhook.channel_id = 5002
    webhook.id = 9998
    mock_guild.webhooks.return_value = [webhook]

    await cache._poll_guild(mock_guild)

    assert 5002 not in cache._webhooks
    assert 9998 not in cache.webhook_ids


async def test_poll_guild_handles_multiple_webhooks(
    cache: WebhookCache,
    mock_guild,
    mock_user,
):
    """Test that _poll_guild handles multiple webhooks in same guild."""
    webhook1 = MagicMock(spec=discord.Webhook)
    webhook1.user = mock_user
    webhook1.channel_id = 5001
    webhook1.id = 1001

    webhook2 = MagicMock(spec=discord.Webhook)
    webhook2.user = mock_user
    webhook2.channel_id = 5002
    webhook2.id = 1002

    mock_guild.webhooks.return_value = [webhook1, webhook2]

    await cache._poll_guild(mock_guild)

    assert 5001 in cache._webhooks
    assert 5002 in cache._webhooks
    assert 1001 in cache.webhook_ids
    assert 1002 in cache.webhook_ids


# Guilds without server-wide Manage Webhooks


def forbidden() -> discord.Forbidden:
    """A Forbidden error, as Discord raises without permission."""
    response = MagicMock(status=403, reason="Forbidden")
    return discord.Forbidden(response, "Missing Permissions")


@pytest.fixture
def unpollable_channel(mock_channel: MockChannel) -> MockChannel:
    """A channel whose guild won't list its webhooks."""
    mock_channel.guild.webhooks.side_effect = forbidden()
    return mock_channel


async def test_poll_guild_without_permission(cache: WebhookCache, mock_guild: MockGuild):
    """A guild that won't list its webhooks is checked channel by channel."""
    mock_guild.webhooks.side_effect = forbidden()

    await cache._poll_guild(mock_guild)

    assert mock_guild.id in cache._guilds_polled
    assert mock_guild.id in cache._unpollable_guilds


async def test_prep_webhook_finds_channel_webhook(
    cache: WebhookCache, unpollable_channel: MockChannel, mock_webhook: MockWebhook
):
    """Without a guild poll, an existing webhook is found in the channel."""
    unpollable_channel.webhooks.return_value = [mock_webhook]

    result = await cache.prep_webhook(unpollable_channel)

    assert result == mock_webhook
    assert mock_webhook.id in cache.webhook_ids
    unpollable_channel.create_webhook.assert_not_called()


async def test_prep_webhook_ignores_other_bots_channel_webhooks(
    cache: WebhookCache,
    unpollable_channel: MockChannel,
    mock_webhook: MockWebhook,
    other_user: MockUser,
):
    """Another bot's webhook in the channel isn't used."""
    foreign = MagicMock(spec=discord.Webhook)
    foreign.user = other_user
    unpollable_channel.webhooks.return_value = [foreign]
    unpollable_channel.create_webhook.return_value = mock_webhook

    result = await cache.prep_webhook(unpollable_channel)

    assert result == mock_webhook
    unpollable_channel.create_webhook.assert_called_once()


async def test_prep_webhook_creates_in_unpollable_guild(
    cache: WebhookCache, unpollable_channel: MockChannel, mock_webhook: MockWebhook
):
    """Without a guild poll, a webhook is created if the channel has none."""
    unpollable_channel.create_webhook.return_value = mock_webhook

    result = await cache.prep_webhook(unpollable_channel)

    assert result == mock_webhook
    unpollable_channel.webhooks.assert_awaited_once()


async def test_prep_webhook_caches_channel_lookup(
    cache: WebhookCache, unpollable_channel: MockChannel, mock_webhook: MockWebhook
):
    """A channel's webhook is only looked up once."""
    unpollable_channel.webhooks.return_value = [mock_webhook]

    await cache.prep_webhook(unpollable_channel)
    await cache.prep_webhook(unpollable_channel)

    unpollable_channel.webhooks.assert_awaited_once()
    unpollable_channel.guild.webhooks.assert_awaited_once()


async def test_prep_webhook_trusts_guild_poll(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """After a successful guild poll, channels aren't checked again."""
    mock_channel.create_webhook.return_value = mock_webhook

    await cache.prep_webhook(mock_channel)

    mock_channel.webhooks.assert_not_called()


async def test_prep_webhook_without_channel_permission(
    cache: WebhookCache, unpollable_channel: MockChannel
):
    """Without Manage Webhooks in the channel either, Forbidden is raised."""
    unpollable_channel.webhooks.side_effect = forbidden()

    with pytest.raises(discord.Forbidden):
        await cache.prep_webhook(unpollable_channel)


async def test_matching_webhook_finds_channel_webhook(
    cache: WebhookCache, unpollable_channel: MockChannel, mock_webhook: MockWebhook
):
    """Without a guild poll, matching_webhook finds the channel's webhook."""
    unpollable_channel.webhooks.return_value = [mock_webhook]

    result = await cache.matching_webhook(unpollable_channel, mock_webhook.id)

    assert result == mock_webhook


# prep_webhook Tests


async def test_prep_webhook_polls_guild_if_not_polled(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that prep_webhook polls guild if not already polled."""
    mock_channel.guild.webhooks.return_value = [mock_webhook]
    mock_channel.create_webhook.return_value = mock_webhook

    await cache.prep_webhook(mock_channel)

    assert mock_channel.guild.id in cache._guilds_polled


async def test_prep_webhook_doesnt_repoll_guild(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that prep_webhook doesn't re-poll already polled guild."""
    mock_channel.guild.webhooks.return_value = [mock_webhook]
    cache._guilds_polled.add(mock_channel.guild.id)

    await cache.prep_webhook(mock_channel)

    # Should not call guild.webhooks() since already polled
    mock_channel.guild.webhooks.assert_not_called()


async def test_prep_webhook_returns_cached_webhook(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that prep_webhook returns cached webhook if exists."""
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook

    result = await cache.prep_webhook(mock_channel)

    assert result == mock_webhook
    mock_channel.create_webhook.assert_not_called()


async def test_prep_webhook_creates_new_webhook(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that prep_webhook creates new webhook if not cached."""
    cache._guilds_polled.add(mock_channel.guild.id)
    mock_channel.create_webhook.return_value = mock_webhook

    result = await cache.prep_webhook(mock_channel)

    assert result == mock_webhook
    mock_channel.create_webhook.assert_called_once_with(name="Inconnuhook", reason="For Roleposts")


async def test_prep_webhook_adds_to_cache_when_creating(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that prep_webhook adds new webhook to all caches."""
    cache._guilds_polled.add(mock_channel.guild.id)
    mock_channel.create_webhook.return_value = mock_webhook

    await cache.prep_webhook(mock_channel)

    assert mock_channel.id in cache._webhooks
    assert cache._webhooks[mock_channel.id] == mock_webhook
    assert mock_webhook.id in cache.webhook_ids


async def test_concurrent_prep_webhook_creates_one(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """Simultaneous posts in a new channel share one new webhook."""

    async def create_webhook(**_: str) -> MockWebhook:
        """Yield mid-creation, as the real API call would."""
        await asyncio.sleep(0)
        return mock_webhook

    mock_channel.create_webhook.side_effect = create_webhook

    results = await asyncio.gather(*(cache.prep_webhook(mock_channel) for _ in range(3)))

    assert results == [mock_webhook] * 3
    mock_channel.create_webhook.assert_awaited_once()


# matching_webhook Tests


async def test_matching_webhook_polls_guild_if_not_polled(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that matching_webhook polls guild if not already polled."""
    mock_channel.guild.webhooks.return_value = [mock_webhook]

    await cache.matching_webhook(mock_channel, mock_webhook.id)

    assert mock_channel.guild.id in cache._guilds_polled


async def test_matching_webhook_returns_webhook_when_id_matches(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that matching_webhook returns webhook when cached and ID matches."""
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook

    result = await cache.matching_webhook(mock_channel, mock_webhook.id)

    assert result == mock_webhook


async def test_matching_webhook_returns_none_when_id_mismatch(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that matching_webhook returns None when cached but ID doesn't match."""
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook

    result = await cache.matching_webhook(mock_channel, 9999)

    assert result is None


async def test_matching_webhook_returns_none_when_not_cached(cache: WebhookCache, mock_channel):
    """Test that matching_webhook returns None when channel not in cache."""
    cache._guilds_polled.add(mock_channel.guild.id)

    result = await cache.matching_webhook(mock_channel, 1001)

    assert result is None


# forget Tests


def test_forget_drops_webhook(cache: WebhookCache, mock_webhook: MockWebhook):
    """A forgotten webhook leaves the cache, but its ID stays known."""
    cache._webhooks[mock_webhook.channel_id] = mock_webhook
    cache.webhook_ids.add(mock_webhook.id)

    cache.forget(mock_webhook)

    assert mock_webhook.channel_id not in cache._webhooks
    assert mock_webhook.id in cache.webhook_ids


def test_forget_keeps_replacement(
    cache: WebhookCache, mock_webhook: MockWebhook, mock_user: MockUser
):
    """Forgetting an old webhook doesn't drop the one that replaced it."""
    replacement = MagicMock(spec=discord.Webhook, id=mock_webhook.id + 1, user=mock_user)
    cache._webhooks[mock_webhook.channel_id] = replacement

    cache.forget(mock_webhook)

    assert cache._webhooks[mock_webhook.channel_id] == replacement


# update_webhooks Tests


async def test_update_webhooks_keeps_just_created_webhook(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """The update event for a webhook we just created leaves it cached."""
    mock_channel.create_webhook.return_value = mock_webhook
    await cache.prep_webhook(mock_channel)
    mock_channel.webhooks.return_value = [mock_webhook]

    await cache.update_webhooks(mock_channel)

    assert cache._webhooks[mock_channel.id] == mock_webhook


async def test_update_webhooks_after_failed_creation(
    cache: WebhookCache, mock_channel: MockChannel, mock_webhook: MockWebhook
):
    """A failed creation doesn't stop the cache noticing a later deletion."""
    mock_channel.create_webhook.side_effect = forbidden()
    with pytest.raises(discord.Forbidden):
        await cache.prep_webhook(mock_channel)
    cache._webhooks[mock_channel.id] = mock_webhook
    mock_channel.webhooks.return_value = []

    await cache.update_webhooks(mock_channel)

    assert mock_channel.id not in cache._webhooks


async def test_update_webhooks_skips_if_guild_not_polled(
    cache: WebhookCache,
    mock_channel,
):
    """Test that update_webhooks skips if guild not polled."""
    await cache.update_webhooks(mock_channel)

    mock_channel.webhooks.assert_not_called()


async def test_update_webhooks_skips_if_channel_not_cached(
    cache: WebhookCache,
    mock_channel,
):
    """Test that update_webhooks skips if channel not in _webhooks."""
    cache._guilds_polled.add(mock_channel.guild.id)

    await cache.update_webhooks(mock_channel)

    mock_channel.webhooks.assert_not_called()


async def test_update_webhooks_removes_deleted_webhook(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that update_webhooks removes webhook from cache if deleted."""
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook
    mock_channel.webhooks.return_value = []  # Webhook deleted

    await cache.update_webhooks(mock_channel)

    assert mock_channel.id not in cache._webhooks


async def test_update_webhooks_keeps_existing_webhook(
    cache: WebhookCache,
    mock_channel,
    mock_webhook,
):
    """Test that update_webhooks leaves webhook in cache if still exists."""
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook
    cache.webhook_ids.add(mock_webhook.id)
    mock_channel.webhooks.return_value = [mock_webhook]  # Still exists

    await cache.update_webhooks(mock_channel)

    assert mock_channel.id in cache._webhooks


async def test_update_webhooks_removes_deleted_despite_other_webhook(
    cache: WebhookCache,
    mock_channel: MockChannel,
    mock_webhook: MockWebhook,
    mock_user: MockUser,
):
    """The cached webhook is dropped when deleted, even if another of ours
    remains in the channel."""
    other = MagicMock(spec=discord.Webhook)
    other.id = mock_webhook.id + 1
    other.user = mock_user
    cache._guilds_polled.add(mock_channel.guild.id)
    cache._webhooks[mock_channel.id] = mock_webhook
    mock_channel.webhooks.return_value = [other]

    await cache.update_webhooks(mock_channel)

    assert mock_channel.id not in cache._webhooks


# webhook_home Tests


def make_thread(parent: object) -> MockThread:
    """A thread in the given parent channel."""
    thread = MagicMock(spec=discord.Thread, id=6001)
    thread.parent = parent  # Mock() treats parent= as its own argument
    return thread


@pytest.mark.parametrize("parent_type", [discord.TextChannel, discord.ForumChannel])
def test_webhook_home_of_channel(parent_type: type):
    """Text and forum channels hold their own webhooks."""
    channel = MagicMock(spec=parent_type)

    assert webhook_home(channel) == (channel, None)


@pytest.mark.parametrize("parent_type", [discord.TextChannel, discord.ForumChannel])
def test_webhook_home_of_thread(parent_type: type):
    """A thread's webhooks belong to its parent."""
    parent = MagicMock(spec=parent_type)
    thread = make_thread(parent)

    assert webhook_home(thread) == (parent, thread)


@pytest.mark.parametrize(
    "channel",
    [
        MagicMock(spec=discord.VoiceChannel),
        MagicMock(spec=discord.DMChannel),
        make_thread(None),  # Parent not cached
        None,
    ],
)
def test_webhook_home_unavailable(channel: object):
    """Other channels, and threads whose parent is unknown, have no webhooks."""
    assert webhook_home(channel) is None


# ChannelWebhook Tests


@pytest.fixture
def raw_webhook() -> MockWebhook:
    """A Discord webhook."""
    return AsyncMock(spec=discord.Webhook, id=1001)


def test_channel_webhook_id(raw_webhook: MockWebhook):
    """The wrapper has its webhook's ID."""
    assert ChannelWebhook(raw_webhook).id == 1001


async def test_channel_webhook_in_channel(raw_webhook: MockWebhook):
    """Outside a thread, calls pass no thread."""
    webhook = ChannelWebhook(raw_webhook)

    await webhook.send(content="Hi")
    await webhook.edit_message(1, content="Edited")
    await webhook.delete_message(1)

    raw_webhook.send.assert_awaited_once_with(wait=True, content="Hi")
    raw_webhook.edit_message.assert_awaited_once_with(1, content="Edited")
    raw_webhook.delete_message.assert_awaited_once_with(1, thread_id=None)


async def test_channel_webhook_in_thread(raw_webhook: MockWebhook):
    """In a thread, every call passes the thread."""
    thread = make_thread(MagicMock(spec=discord.TextChannel))
    webhook = ChannelWebhook(raw_webhook, thread)

    await webhook.send(content="Hi")
    await webhook.edit_message(1, content="Edited")
    await webhook.delete_message(1)

    raw_webhook.send.assert_awaited_once_with(wait=True, thread=thread, content="Hi")
    raw_webhook.edit_message.assert_awaited_once_with(1, thread=thread, content="Edited")
    raw_webhook.delete_message.assert_awaited_once_with(1, thread_id=thread.id)
