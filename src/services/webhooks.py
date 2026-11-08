"""Webhooks for Roleposts and headers."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import discord
from loguru import logger

UNKNOWN_WEBHOOK = 10015  # Discord's error code for a deleted webhook

# Threads have no webhooks of their own; they use their parent's
type WebhookChannel = discord.TextChannel | discord.ForumChannel


def webhook_home(channel: object) -> tuple[WebhookChannel, discord.Thread | None] | None:
    """The channel whose webhooks can post in the given channel, and the thread
    they'd post in, if any. None if webhooks can't post there."""
    thread = channel if isinstance(channel, discord.Thread) else None
    parent = thread.parent if thread is not None else channel
    if isinstance(parent, (discord.TextChannel, discord.ForumChannel)):
        return parent, thread
    return None


@dataclass(frozen=True)
class ChannelWebhook:
    """A webhook bound to where it posts: its own channel, or one of that
    channel's threads. Every call passes the thread, which Discord needs to
    find the thread's messages."""

    webhook: discord.Webhook
    thread: discord.Thread | None = None

    @property
    def id(self) -> int:
        """The webhook's ID, which is also its messages' author ID."""
        return self.webhook.id

    def _target(self) -> dict[str, discord.Thread]:
        """The thread argument, if posting in a thread."""
        return {"thread": self.thread} if self.thread is not None else {}

    async def send(self, **kwargs: Any) -> discord.WebhookMessage:
        """Send a message, waiting for it."""
        return await self.webhook.send(wait=True, **self._target(), **kwargs)

    async def edit_message(self, message_id: int, **kwargs: Any) -> discord.WebhookMessage:
        """Edit one of the webhook's messages."""
        return await self.webhook.edit_message(message_id, **self._target(), **kwargs)

    async def delete_message(self, message_id: int):
        """Delete one of the webhook's messages."""
        thread_id = self.thread.id if self.thread is not None else None
        await self.webhook.delete_message(message_id, thread_id=thread_id)


class WebhookCache:
    """Maintains an active cache of webhooks."""

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self._webhooks: dict[int, discord.Webhook] = {}
        self.webhook_ids: set[int] = set()
        self._guilds_polled: set[int] = set()
        # Guilds whose webhooks must be found channel by channel, because
        # Manage Webhooks is only granted in some channels
        self._unpollable_guilds: set[int] = set()
        # Concurrent posts in a new channel must not each create a webhook
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        logger.info("Created cache for bot ID {}", bot_id)

    def _is_ours(self, webhook: discord.Webhook) -> bool:
        """Whether the bot created the webhook."""
        return webhook.user is not None and webhook.user.id == self.bot_id

    async def _check_webhook(self, channel: WebhookChannel, webhook_id: int) -> bool:
        """Check that the webhook still exists in the channel. Another of our
        webhooks there doesn't count, since the cache would keep using the
        missing one."""
        for _webhook in await channel.webhooks():
            if _webhook.id == webhook_id:
                logger.info(
                    "{} found in #{} on {}",
                    _webhook.name,
                    channel.name,
                    channel.guild.name,
                )
                return True

        logger.info("Webhook not found in #{} on {}", channel.name, channel.guild.name)
        return False

    async def _poll_guild(self, guild: discord.Guild):
        """Get all of the guild's webhooks."""
        logger.info("Pulling {}'s webhooks", guild.name)
        try:
            webhooks = await guild.webhooks()
        except discord.Forbidden:
            # Listing a guild's webhooks needs Manage Webhooks server-wide.
            # Without it, channels are checked as they're used.
            logger.info("Can't list {}'s webhooks; checking by channel", guild.name)
            self._unpollable_guilds.add(guild.id)
            webhooks = []

        for webhook in webhooks:
            if self._is_ours(webhook) and webhook.channel_id is not None:
                logger.debug(
                    "Webhook {} found in #{} ({})",
                    webhook.name,
                    webhook.channel.name if webhook.channel is not None else "UNKNOWN",
                    guild.name,
                )
                self._webhooks[webhook.channel_id] = webhook
                self.webhook_ids.add(webhook.id)

        self._guilds_polled.add(guild.id)

    async def _load_channel(self, channel: WebhookChannel):
        """Load the channel's webhook into the cache, if we have one there.
        Raises Forbidden."""
        if channel.guild.id not in self._guilds_polled:
            await self._poll_guild(channel.guild)

        if channel.id in self._webhooks or channel.guild.id not in self._unpollable_guilds:
            # The guild poll already found every webhook we have
            return

        for webhook in await channel.webhooks():
            if self._is_ours(webhook):
                logger.debug("Found {} in #{}", webhook.name, channel.name)
                self._webhooks[channel.id] = webhook
                self.webhook_ids.add(webhook.id)
                return

    async def prep_webhook(self, channel: WebhookChannel) -> discord.Webhook:
        """Prepare a webhook, either from the cache or creating one. Raises Forbidden."""
        async with self._locks[channel.id]:
            await self._load_channel(channel)

            if channel.id not in self._webhooks:
                # Create the webhook
                webhook = await channel.create_webhook(name="Inconnuhook", reason="For Roleposts")
                self._webhooks[channel.id] = webhook
                self.webhook_ids.add(webhook.id)
                logger.info(
                    "Created a webhook in #{} on {}",
                    channel.name,
                    channel.guild.name,
                )
            else:
                logger.debug(
                    "Using cached webhook in #{} ({})",
                    channel.name,
                    channel.guild.name,
                )

            return self._webhooks[channel.id]

    def _drop(self, channel_id: int, webhook_id: int) -> bool:
        """Remove the channel's cached webhook, but only if it's still the given
        one; a replacement may have been cached since. Returns whether it was
        removed. Its ID stays known, since its old messages still carry it."""
        cached = self._webhooks.get(channel_id)
        if cached is None or cached.id != webhook_id:
            return False
        del self._webhooks[channel_id]
        return True

    def forget(self, webhook: discord.Webhook):
        """Drop a cached webhook that Discord says no longer exists."""
        if webhook.channel_id is not None and self._drop(webhook.channel_id, webhook.id):
            logger.info("Forgot deleted webhook {}", webhook.id)

    async def matching_webhook(
        self,
        channel: WebhookChannel,
        webhook_id: int,
    ) -> discord.Webhook | None:
        """Our webhook in the channel, if it has the given ID (as when a
        message came from it). Raises Forbidden."""
        await self._load_channel(channel)

        cached = self._webhooks.get(channel.id)
        if cached is not None and cached.id == webhook_id:
            return cached

        # A channel can hold more than one of our webhooks (from before the
        # cache was race-free), and only one is cached. Only look further for
        # an ID we know, or could have missed in a guild we can't poll.
        known = webhook_id in self.webhook_ids
        if not known and channel.guild.id not in self._unpollable_guilds:
            return None

        for webhook in await channel.webhooks():
            if webhook.id == webhook_id and self._is_ours(webhook):
                logger.debug("Found uncached webhook {} in #{}", webhook.id, channel.name)
                self.webhook_ids.add(webhook.id)
                return webhook

        return None

    async def update_webhooks(self, channel: WebhookChannel):
        """Check if the webhook was deleted or not."""
        logger.debug("Checking webhook updates in #{}", channel.name)
        if channel.guild.id not in self._guilds_polled:
            logger.debug("Ignoring #{} (guild not loaded)", channel.name)
            return

        if channel.id not in self._webhooks:
            logger.debug("Ignoring #{} ({}) (no webhooks loaded)", channel.name, channel.guild.name)
            return

        # We've previously fetched this channel's webhooks, so we need to check
        # if our webhook has been deleted. The cache may change while we wait.
        webhook_id = self._webhooks[channel.id].id
        if not await self._check_webhook(channel, webhook_id) and self._drop(
            channel.id, webhook_id
        ):
            logger.info("Webhook deleted in #{} ({})", channel.name, channel.guild.name)
