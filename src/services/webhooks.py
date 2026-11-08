"""Class package."""

import asyncio
from collections import defaultdict

import discord
from loguru import logger

UNKNOWN_WEBHOOK = 10015  # Discord's error code for a deleted webhook


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

    async def _check_webhook(self, channel: discord.TextChannel, webhook_id: int) -> bool:
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

    async def _load_channel(self, channel: discord.TextChannel):
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

    async def prep_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
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
                logger.info(
                    "Using CACHED webhook in #{} ({})",
                    channel.name,
                    channel.guild.name,
                )

            return self._webhooks[channel.id]

    def forget(self, webhook: discord.Webhook):
        """Drop a cached webhook that Discord says no longer exists. Its ID
        stays known, since its old messages still carry it."""
        if webhook.channel_id is None:
            return
        cached = self._webhooks.get(webhook.channel_id)
        if cached is not None and cached.id == webhook.id:
            del self._webhooks[webhook.channel_id]
            logger.info("Forgot deleted webhook {}", webhook.id)

    async def matching_webhook(
        self,
        channel: discord.TextChannel,
        webhook_id: int,
    ) -> discord.Webhook | None:
        """Our webhook in the channel, if it has the given ID (as when a
        message came from it). Raises Forbidden."""
        await self._load_channel(channel)

        if webhook := self._webhooks.get(channel.id):
            logger.debug("Found Webhook ID# {}", webhook.id)
            if webhook.id == webhook_id:
                return webhook
            else:
                logger.debug("Webhook found, but the ID doesn't match")
        else:
            logger.debug("No Webhook found with ID# {}", webhook_id)

        return None

    async def update_webhooks(self, channel: discord.TextChannel):
        """Check if the webhook was deleted or not."""
        logger.debug("Checking webhook updates in #{}", channel.name)
        if channel.guild.id not in self._guilds_polled:
            logger.debug("Ignoring #{} (guild not loaded)", channel.name)
            return

        if channel.id not in self._webhooks:
            logger.debug("Ignoring #{} ({}) (no webhooks loaded)", channel.name, channel.guild.name)
            return

        # We've previously fetched this channel's webhooks, so we need to check
        # if our webhook has been deleted
        if not await self._check_webhook(channel, self._webhooks[channel.id].id):
            del self._webhooks[channel.id]
            logger.info("Webhook deleted in #{} ({})", channel.name, channel.guild.name)
