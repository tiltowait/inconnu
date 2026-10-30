"""Bot instance and event handlers."""

import asyncio
from datetime import datetime
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
from services.reporter import reporter
from utils import cmd_replace_respond, raw_command_options

# Commands where the character option is needed even when the user has only one character
CHARACTER_OPTION_REQUIRED = frozenset(
    {
        "character bio edit",
        "character delete",
        "experience remove entry",
        "experience award",
        "experience deduct",
        "update header",
        "transfer",
    }
)
# Commands that shouldn't show the MOTD
MOTD_EXEMPT = frozenset({"motd", "announce"})


class InconnuBot(discord.AutoShardedBot):
    """Adds minor functionality over the superclass. All commands in cogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.welcomed = False
        self.connected = False
        self.lockdown: datetime | None = None
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
        """Whether the bot has manage webhooks permission in the channel."""
        if not isinstance(channel, discord.TextChannel):
            return False
        return channel.permissions_for(channel.guild.me).manage_webhooks

    async def prep_webhook(
        self,
        channel: Channel,
    ) -> discord.Webhook:
        """Prepare a webhook, either from the cache or creating one. Raises WebhookError."""
        if not isinstance(channel, discord.TextChannel):
            raise ValueError("Webhooks are only supported in text channels.")
        try:
            return await self.webhook_cache.prep_webhook(channel)
        except discord.Forbidden:
            raise errors.WebhookError("Inconnu needs `Manage Webhook` permission for this command.")
        except AttributeError:
            raise errors.WebhookError("This feature isn't available in threads.")

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

        if interaction.type == discord.InteractionType.application_command:
            # Insert the raw interaction data in case we get a crash before
            # on_application_command() can perform its own insert. This creates
            # duplicate data; in the future, these routines will be merged.
            inter_data = {
                "guild": interaction.guild_id,
                "user": interaction.user.id if interaction.user else None,
            }
            if interaction.data is not None:
                inter_data.update(cast(dict[str, Any], interaction.data))
            await db.interactions.insert_one(inter_data)

        await self.process_application_commands(interaction)

    async def on_application_command(self, ctx: AppCtx):
        """Show tips and the MOTD after a command."""
        await self._tip_unneeded_character_option(ctx)
        await self._show_motd(ctx)

    async def _tip_unneeded_character_option(self, ctx: AppCtx):
        """Tell a user with one character they don't need the character option."""
        assert ctx.command is not None
        options = raw_command_options(ctx.interaction)
        if "character" not in options or "player" in options:
            return
        if ctx.guild is None or ctx.command.qualified_name in CHARACTER_OPTION_REQUIRED:
            return

        member = cast(discord.Member, ctx.user)
        if await services.char_mgr.character_count(ctx.guild, member) != 1:
            return

        # They may have used an SPC, which doesn't count toward their characters
        try:
            character = await services.char_mgr.fetchone(ctx.guild, member, options["character"])
        except errors.CharacterNotFoundError:
            return
        if not character.is_pc:
            return

        await asyncio.sleep(1)  # Make sure it shows after the command
        tip = (
            "**Tip:** You only have one character, so you don't need "
            f"the `character` option for `/{ctx.command.qualified_name}`."
        )
        await cmd_replace_respond(ctx, tip, ephemeral=True)

    async def _show_motd(self, ctx: AppCtx):
        """Show the MOTD once per user."""
        assert ctx.command is not None
        if self.motd is None or ctx.command.qualified_name in MOTD_EXEMPT:
            return
        if ctx.user.id in self.motd_given:
            return

        logger.debug("Showing MOTD to {}", ctx.user.name)
        await asyncio.sleep(1)
        try:
            await cmd_replace_respond(ctx, embed=self.motd, ephemeral=True)
            self.motd_given.add(ctx.user.id)
        except discord.HTTPException:
            logger.warning("Could not show MOTD to {}", ctx.user.name)

    async def on_connect(self):
        """Perform early setup."""
        if not self.user or not self.user.id:
            raise RuntimeError("Did not receive a user ID. Crashing.")

        if not self.connected:
            await reporter.prepare_channel(self)
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

    async def on_application_command_error(
        self, context: discord.ApplicationContext, exception: discord.DiscordException
    ):
        """Use centralized reporter to handle errors."""
        await reporter.report_error(cast(AppCtx, context), exception)

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
