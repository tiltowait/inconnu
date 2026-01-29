"""Class package."""

import discord
from loguru import logger


class WebhookCache:
    """Maintains an active cache of webhooks."""

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self._webhooks: dict[int, discord.Webhook] = {}
        self.webhook_ids: set[int] = set()
        self._guilds_polled: set[int] = set()
        self.just_created: set[int] = set()

        logger.info("WEBHOOK: Created cache for bot ID {}", bot_id)

    async def _check_webhook(self, channel: discord.TextChannel) -> bool:
        """Check that we have a webhook in the channel."""
        for _webhook in await channel.webhooks():
            if _webhook.user is not None and _webhook.user.id == self.bot_id:
                logger.info(
                    "WEBHOOK: {} found in #{} on {}",
                    _webhook.name,
                    channel.name,
                    channel.guild.name,
                )
                return True

        logger.info("WEBHOOK: Not found in #{} on {}", channel.name, channel.guild.name)
        return False

    async def _poll_guild(self, guild: discord.Guild):
        """Get all of the guild's webhooks."""
        logger.info("WEBHOOK: Pulling {}'s webhooks", guild.name)
        for webhook in await guild.webhooks():
            if (
                webhook.user is not None
                and webhook.user.id == self.bot_id
                and webhook.channel_id is not None
            ):
                logger.debug(
                    "WEBHOOK: Webhook {} found in #{} ({})",
                    webhook.name,
                    webhook.channel.name if webhook.channel is not None else "UNKNOWN",
                    guild.name,
                )
                self._webhooks[webhook.channel_id] = webhook
                self.webhook_ids.add(webhook.id)

        self._guilds_polled.add(guild.id)

    async def prep_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Prepare a webhook, either from the cache or creating one. Raises Forbidden."""
        if channel.guild.id not in self._guilds_polled:
            await self._poll_guild(channel.guild)

        if channel.id not in self._webhooks:
            # Create the webhook
            self.just_created.add(channel.id)
            webhook = await channel.create_webhook(name="Inconnuhook", reason="For Roleposts")
            self._webhooks[channel.id] = webhook
            self.webhook_ids.add(webhook.id)
            logger.info(
                "WEBHOOK: Created a webhook in #{} on {}",
                channel.name,
                channel.guild.name,
            )
        else:
            logger.info(
                "WEBHOOK: Using CACHED webhook in #{} ({})",
                channel.name,
                channel.guild.name,
            )

        return self._webhooks[channel.id]

    async def fetch_webhook(
        self,
        channel: discord.TextChannel,
        webhook_id: int,
    ) -> discord.Webhook | None:
        """Fetch a webhook for a particular guild."""
        if channel.guild.id not in self._guilds_polled:
            await self._poll_guild(channel.guild)

        if webhook := self._webhooks.get(channel.id):
            logger.debug("WEBHOOK: Found Webhook ID# {}", webhook.id)
            if webhook.id == webhook_id:
                return webhook
            else:
                logger.debug("WEBHOOK: Webhook found, but the ID doesn't match")
        else:
            logger.debug("WEBHOOK: No Webhook found with ID# {}", webhook_id)

        return None

    async def update_webhooks(self, channel: discord.TextChannel):
        """Check if the webhook was deleted or not."""
        logger.debug("WEBHOOK: Checking webhook updates in #{}", channel.name)
        if channel.id in self.just_created:
            logger.debug("WEBHOOK: Ignoring just-created webhook")
            self.just_created.remove(channel.id)
            return

        if channel.guild.id not in self._guilds_polled:
            logger.debug("WEBHOOK: Ignoring #{} (guild not loaded)", channel.name)
            return

        if channel.id not in self._webhooks:
            logger.debug(
                "WEBHOOK: Ignoring #{} ({}) (no webhooks loaded)", channel.name, channel.guild.name
            )
            return

        # We've previously fetched this channel's webhooks, so we need to check
        # if our webhook has been deleted
        if not await self._check_webhook(channel):
            del self._webhooks[channel.id]
            logger.info("WEBHOOK: Webhook deleted in #{} ({})", channel.name, channel.guild.name)
