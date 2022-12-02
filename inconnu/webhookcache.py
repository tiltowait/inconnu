"""Class package."""

import discord

from logger import Logger


class WebhookCache:
    """Maintains an active cache of webhooks."""

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self._webhooks: dict[int, discord.Webhook] = {}
        self.webhook_ids: set[int] = set()
        self._guilds_polled: set[int] = set()
        self.just_created: set[int] = set()

        Logger.info("WEBHOOK: Created cache for bot ID %s", bot_id)

    async def _fetch_webhook(self, channel: discord.TextChannel):
        """Find the appropriate webhook in the channel."""
        for _webhook in await channel.webhooks():
            if _webhook.user.id == self.bot_id:
                Logger.info(
                    "WEBHOOK: %s found in #%s on %s",
                    _webhook.name,
                    channel.name,
                    channel.guild.name,
                )
                self.webhook_ids.add(_webhook.id)
                return _webhook

        Logger.info("WEBHOOK: Not found in #%s on %s", channel.name, channel.guild.name)
        return None

    async def _poll_guild(self, guild: discord.Guild):
        """Get all of the guild's webhooks."""
        Logger.info("WEBHOOK: Pulling %s's webhooks", guild.name)
        for webhook in await guild.webhooks():
            if webhook.user.id == self.bot_id and webhook.channel_id is not None:
                Logger.debug(
                    "WEBHOOK: Webhook %s found in #%s (%s)",
                    webhook.name,
                    webhook.channel.name,
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
            webhook = await channel.create_webhook(name="Inconnuhook", reason="For RP posts")
            self._webhooks[channel.id] = webhook
            self.webhook_ids.add(webhook.id)
            Logger.info(
                "WEBHOOK: Created a webhook in #%s on %s",
                channel.name,
                channel.guild.name,
            )
        else:
            Logger.info(
                "WEBHOOK: Using CACHED webhook in #%s (%s)",
                channel.name,
                channel.guild.name,
            )

        return self._webhooks[channel.id]

    async def fetch_webhook(self, channel: discord.TextChannel, webhook_id: int):
        """Fetch a webhook for a particular guild."""
        if channel.guild.id not in self._guilds_polled:
            await self._poll_guild(channel.guild)

        if webhook := self._webhooks.get(channel.id):
            Logger.debug("WEBHOOK: Found Webhook ID# %s", webhook.id)
            if webhook.id == webhook_id:
                return webhook
            else:
                Logger.debug("WEBHOOK: Webhook found, but the ID doesn't match")
                return None
        else:
            Logger.debug("WEBHOOK: No Webhook found with ID# %s", webhook_id)

        return webhook

    async def update_webhooks(self, channel: discord.TextChannel):
        """Check if the webhook was deleted or not."""
        Logger.debug("WEBHOOK: Checking webhook updates in #%s", channel.name)
        if channel.id in self.just_created:
            Logger.debug("WEBHOOK: Ignoring just-created webhook")
            self.just_created.remove(channel.id)
            return

        if channel.guild.id not in self._guilds_polled:
            Logger.debug("WEBHOOK: Ignoring #%s (guild not loaded)", channel.name)
            return

        if channel.id not in self._webhooks:
            Logger.debug(
                "WEBHOOK: Ignoring #%s (%s) (no webhooks loaded)", channel.name, channel.guild.name
            )
            return

        # We've previously fetched this channel's webhooks, so we need to check
        # if our webhook has been deleted
        webhook = await self._fetch_webhook(channel)
        if webhook is None:
            del self._webhooks[channel.id]
            Logger.info("WEBHOOK: Webhook deleted in #%s (%s)", channel.name, channel.guild.name)
