"""Bot instance and event handlers."""

from pathlib import Path
from typing import Any, cast

import discord
from cachetools import TTLCache
from loguru import logger

import db
import errors
import inconnu
import services
from config import settings
from ctx import AppCtx, Channel
from models import RPPost, VChar
from services import WebhookCache
from services.lockdown import LOCKDOWN_DELAY, Lockdown, LockdownReason
from services.webhooks import UNKNOWN_WEBHOOK, ChannelWebhook, webhook_home


class InconnuBot(discord.AutoShardedBot):
    """Adds minor functionality over the superclass. All commands in cogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.welcomed = False
        self.connected = False
        self.lockdown: Lockdown | None = None
        self.motd: discord.Embed | None = None
        self.motd_given: set[int] = set()
        self._webhook_cache: WebhookCache | None = None
        self._guild_fetch_failures = TTLCache[int, bool](maxsize=200, ttl=1200)

        self._check_config()
        self._load_cogs()

        logger.info("Bot instantiated")

    def _check_config(self):
        """Check and log various configuration options."""
        if settings.show_test_routes:
            logger.info("Showing test routes")

        logger.info("Profile site set to {}", settings.profile_site)
        logger.info("Admin guild: {}", settings.admin_server)

        if settings.debug_guilds:
            logger.info("Debugging on {}", settings.debug_guilds)

    def _load_cogs(self):
        """Load cogs from the interface package."""
        cog_dir = Path(__file__).parent / "interface"
        for path in cog_dir.glob("*.py"):
            if not path.name.startswith("_"):
                logger.debug("Loading {}", path.name)
                self.load_extension(f"interface.{path.stem}")

        if not self.extensions:
            raise RuntimeError(f"No cogs found in {cog_dir}")

    @property
    def me(self) -> discord.ClientUser:
        """The bot's own user, non-null after login."""
        if self.user is None:
            raise RuntimeError("The bot isn't logged in")
        return self.user

    @property
    def webhook_cache(self) -> WebhookCache:
        """The webhook cache, available after connecting."""
        if self._webhook_cache is None:
            raise RuntimeError("The webhook cache isn't available until the bot connects")
        return self._webhook_cache

    @property
    def invite_url(self) -> str:
        """The bot's invite URL."""
        return discord.utils.oauth_url(
            self.me.id,
            permissions=discord.Permissions(
                send_messages=True,
                manage_webhooks=True,
            ),
            scopes=("applications.commands", "bot"),
        )

    def start_lockdown(self, reason: LockdownReason) -> Lockdown:
        """Lock the bot down ahead of a shutdown in LOCKDOWN_DELAY."""
        self.lockdown = Lockdown(reason, discord.utils.utcnow() + LOCKDOWN_DELAY)
        return self.lockdown

    def end_lockdown(self):
        """Remove the lockdown."""
        self.lockdown = None

    def set_motd(self, embed: discord.Embed | None):
        """Set the MOTD embed."""
        self.motd = embed
        self.motd_given = set()

    async def get_application_context(
        self, interaction: discord.Interaction, cls: type[AppCtx] = AppCtx
    ) -> AppCtx:
        """Build an AppCtx for the interaction."""
        ctx = await super().get_application_context(interaction, cls)
        return cast(AppCtx, ctx)

    async def on_message(self, message: discord.Message):
        """If the message is a reply to a Rolepost, ping the Rolepost's author."""
        if message.author.bot or message.type != discord.MessageType.reply:
            return
        if message.reference is None:
            return

        # The backend doesn't always resolve the reference. We could search the
        # message cache when it doesn't, but for now we skip the message.
        replied_to = message.reference.resolved
        if not isinstance(replied_to, discord.Message):
            return
        # Only works once the webhooks have been fetched
        if replied_to.author.id not in self.webhook_cache.webhook_ids:
            return

        rp_post = await RPPost.find_one({"id_chain": message.reference.message_id})
        if rp_post is None:
            return
        if rp_post.user == message.author.id:
            # Replying to your own post
            return

        # Users can't turn off reply pings to bots, so if the replier didn't
        # already ping the author, we can safely do it for them.
        if rp_post.user in (m.id for m in message.mentions):
            return

        if user := await self.get_or_fetch_user(rp_post.user):
            logger.debug("Pinging {} for a reply to their Rolepost", user.name)
            await message.reply(user.mention, mention_author=False, delete_after=60)

    def cmd_mention(
        self,
        name: str,
        type: type[discord.ApplicationCommand] = discord.ApplicationCommand,
    ) -> str | None:
        """Shorthand for get_application_command(...).mention."""
        if command := self.get_application_command(name, type=type):
            return getattr(command, "mention", None)
        return None

    async def get_or_fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Look up a guild in the guild cache or fetches if not found.

        If fetch fails, then prevent further fetches for until the TTL cache
        times out."""
        guild = self.get_guild(guild_id)
        if guild is None and guild_id not in self._guild_fetch_failures:
            try:
                guild = await self.fetch_guild(guild_id)
            except discord.Forbidden, discord.HTTPException:
                self._guild_fetch_failures[guild_id] = True

        return guild

    def can_webhook(self, channel: Channel) -> bool:
        """Whether webhooks can post in the channel: a text channel or thread,
        with Manage Webhooks permission (a thread's parent holds its
        webhooks)."""
        if (home := webhook_home(channel)) is None:
            return False
        parent = home[0]
        return parent.permissions_for(parent.guild.me).manage_webhooks

    async def prep_webhook(self, channel: Channel) -> ChannelWebhook:
        """Prepare a webhook for the channel or thread, either from the cache or
        creating one. Raises WebhookError."""
        if (home := webhook_home(channel)) is None:
            raise errors.WebhookError(
                "This feature is only available in text channels and threads."
            )
        parent, thread = home
        try:
            webhook = await self.webhook_cache.prep_webhook(parent)
        except discord.Forbidden:
            raise errors.WebhookError("Inconnu needs `Manage Webhook` permission for this command.")
        return ChannelWebhook(webhook, thread)

    async def webhook_send(
        self, channel: Channel, **kwargs: Any
    ) -> tuple[ChannelWebhook, discord.WebhookMessage]:
        """Send a webhook post's first message, returning the webhook for the
        rest. If the channel's webhook was deleted without the cache noticing,
        a new one replaces it. Raises WebhookError."""
        webhook = await self.prep_webhook(channel)
        try:
            return webhook, await webhook.send(**kwargs)
        except discord.NotFound as err:
            if err.code != UNKNOWN_WEBHOOK:
                raise
            self.webhook_cache.forget(webhook.webhook)

        webhook = await self.prep_webhook(channel)
        return webhook, await webhook.send(**kwargs)

    async def _set_presence(self):
        """Set the bot's presence message."""
        servers = len(self.guilds)
        message = f"/help | {servers} chronicles"

        logger.info("Setting presence")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=message)
        )

    # Events

    async def on_interaction(self, interaction: discord.Interaction):
        """Check whether the bot is ready before allowing the interaction to go through."""
        if not services.emojis.loaded:
            await services.emojis.load(self)
        await self.process_application_commands(interaction)

    async def on_connect(self):
        """Perform early setup."""
        if not self.user or not self.user.id:
            raise RuntimeError("Did not receive a user ID. Crashing.")

        if not self.connected:
            self._webhook_cache = WebhookCache(self.user.id)

            logger.info("Logged in as {}!", str(self.user))
            logger.info("{}", discord.version_info)
            logger.info("Latency: {} ms", self.latency * 1000)

            VChar.SPC_OWNER = self.user.id
            logger.info("Registered SPC owner: {}", VChar.SPC_OWNER)

            self.connected = True

        await self.sync_commands()
        logger.info("Commands synced")

    async def on_ready(self):
        """Log startup info and set the presence."""
        if not self.welcomed:
            logger.info("Internal cache built")

            server_info = await db.server_info()
            logger.info(
                "MongoDB version {}, using {} database",
                server_info["version"],
                server_info["database"],
            )

            # Display some vanity stats
            guild_count = len(self.guilds)
            member_count = sum(g.member_count for g in self.guilds)
            logger.info("Caches built: {} guilds. {} members.", guild_count, member_count)

            self.welcomed = True

        # We always want to do these regardless of welcoming or not
        await self._set_presence()
        logger.info("Ready")

    # ErrorListener reports view and modal errors. Unlike command errors, the
    # client's defaults would also print them to stderr, so silence those.

    async def on_view_error(
        self, error: Exception, item: discord.ui.ViewItem, interaction: discord.Interaction
    ):
        """Leave view errors to ErrorListener."""

    async def on_modal_error(self, error: Exception, interaction: discord.Interaction):
        """Leave modal errors to ErrorListener."""

    # Member Events

    async def on_member_remove(self, member: discord.Member):
        """Mark all of a member's characters as inactive."""
        await services.char_mgr.mark_inactive(member)

    async def on_member_join(self, member: discord.Member):
        """Mark all the player's characters as active when they rejoin a guild."""
        await services.char_mgr.mark_active(member)

    # Guild Events

    async def on_guild_join(self, guild: discord.Guild):
        """Log whenever a guild is joined."""
        logger.info("Joined {}!", guild.name)
        await inconnu.stats.guild_joined(guild)
        await self._set_presence()

    async def on_guild_remove(self, guild: discord.Guild):
        """Log guild removals."""
        logger.info("Left {} :(", guild.name)
        await inconnu.stats.guild_left(guild)
        await self._set_presence()

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Log guild name changes."""
        if before.name != after.name:
            logger.info("Renamed {} => {}", before.name, after.name)
            await inconnu.stats.guild_renamed(after, after.name)

    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Update the webhooks cache."""
        await self.webhook_cache.update_webhooks(channel)
