"""Bot instance and event handlers."""

import asyncio
import os
from datetime import time, timezone
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks
from loguru import logger

import config
import inconnu
from config import DEBUG_GUILDS, SUPPORTER_GUILD, SUPPORTER_ROLE
from errorreporter import reporter

if TYPE_CHECKING:
    from inconnu.models import VChar


class InconnuBot(discord.AutoShardedBot):
    """Adds minor functionality over the superclass. All commands in cogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.welcomed = False
        self.connected = False
        self.lockdown = None
        self.wizards = 0
        self.motd = None
        self.motd_given = set()
        self.webhook_cache: inconnu.webhookcache.WebhookCache = None  # type:ignore
        logger.info("BOT: Instantiated")

        if config.SHOW_TEST_ROUTES:
            logger.info("CONFIG: Showing test routes")

        logger.info("CONFIG: Profile site set to {}", config.PROFILE_SITE)
        logger.info("CONFIG: Admin guild: {}", config.ADMIN_GUILD)

        if config.DEBUG_GUILDS:
            logger.info("CONFIG: Debugging on {}", DEBUG_GUILDS)

        # Add the cogs
        for filename in os.listdir("./interface"):
            if filename[0] != "_" and filename.endswith(".py"):
                logger.debug("COGS: Loading {}", filename)
                self.load_extension(f"interface.{filename[:-3]}")

    @property
    def invite_url(self) -> str:
        """The bot's invite URL."""
        return discord.utils.oauth_url(
            self.user.id,
            permissions=discord.Permissions(
                send_messages=True,
                use_external_emojis=True,
                manage_webhooks=True,
            ),
            scopes=("applications.commands", "bot"),
        )

    def set_motd(self, embed: discord.Embed | None):
        """Set the MOTD embed."""
        self.motd = embed
        self.motd_given = set()

    async def on_message(self, message: discord.Message):
        """If the message is a reply to a Rolepost, ping the Rolepost's author."""
        # TODO: Once satisfied with this method, remove most of the debug lines
        if message.author.bot:
            logger.debug("BOT: Disregarding bot message")
            return
        if message.type != discord.MessageType.reply:
            logger.debug("BOT: Disregarding non-reply message.")
            return
        if message.reference is None:
            logger.debug("BOT: Disregarding message with no reference.")
            return

        # It's possible for the backend to not fill in this property, which is
        # why we have to check it. We *could* also search the cached messages,
        # and maybe we'll add that in the future.
        if message.reference.resolved is not None:
            # This routine only works if the webhooks have already been fetched
            if message.reference.resolved.author.id in self.webhook_cache.webhook_ids:
                logger.debug("BOT: Received a reply to one of our webhooks")
                rp_post = await inconnu.models.RPPost.find_one(
                    {"id_chain": message.reference.message_id}
                )
                if rp_post is not None:
                    # Users can't turn off reply pings to bots, so we don't
                    # need to worry about an edge case where they disabled the
                    # reply ping and can safely ping the author.
                    if rp_post.user not in map(lambda m: m.id, message.mentions):
                        logger.debug("BOT: Pinging Rolepost's author")
                        user = await self.get_or_fetch_user(rp_post.user)
                        await message.reply(user.mention, mention_author=False, delete_after=60)
                    else:
                        logger.debug("BOT: Replier pinged the Rolepost's author; doing nothing")
                else:
                    logger.debug("BOT: Rolepost not found")
            else:
                logger.debug("BOT: Disregarding reply that isn't to one of our webhooks")

    @staticmethod
    async def inform_premium_loss(member: discord.Member, title="You are no longer a supporter!"):
        """Inform a member if they lost premium status."""
        try:
            server = f"[Inconnu server]({inconnu.constants.SUPPORT_URL})"
            patreon = f"[patron]({inconnu.constants.PATREON})"
            embed = discord.Embed(
                title=title,
                description=(
                    f"If you aren't a {patreon} by the first of the month, your "
                    "character profile images will be deleted.\n\n"
                    f"To maintain supporter status, you must be on the {server} "
                    f"and a {patreon}.\n\n"
                    "**Note:** Old-style (URL-based) images are grandfathered "
                    "in and will not be removed."
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text="Thank you for your support!")
            await member.send(embed=embed)
            logger.info("PREMIUM: Informed {} about premium loss", member.name)

        except (discord.errors.Forbidden, discord.errors.HTTPException):
            logger.info("PREMIUM: Could not DM {} about premium loss", member.name)

    async def inform_premium_features(self, member: discord.Member):
        """Inform the member of premium features."""
        try:
            upload_mention = self.get_application_command("character image upload").mention
            embed = discord.Embed(
                title="Thank you for your support!",
                description=(
                    f"You may now upload profile images via {upload_mention}. "
                    "(Use it in a server, not from this DM!)\n\n"
                    "[Read more here!](https://docs.inconnu.app/guides/premium/character-images)"
                ),
                color=discord.Color.green(),
            )
            embed.set_footer(
                text=(
                    "You are responsible for the images you upload. "
                    "Violating the terms of service will result in a permanent ban from the bot."
                )
            )
            await member.send(embed=embed)
            logger.info("PREMIUM: Informed {} about premium features", member.name)

        except discord.errors.Forbidden:
            logger.info("PREMIUM: Could not DM {} about premium features", member.name)

    def cmd_mention(
        self, name: str, type: type[discord.ApplicationCommand] = discord.ApplicationCommand
    ) -> str:
        """Shorthand for get_application_command(...).mention."""
        if command := self.get_application_command(name, type=type):
            return command.mention
        return None

    async def get_or_fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Look up a guild in the guild cache or fetches if not found."""
        if guild := self.get_guild(guild_id):
            return guild
        logger.debug("BOT: Guild {} not found in cache; attempting fetch", guild_id)
        return await self.fetch_guild(guild_id)

    def can_webhook(self, channel: discord.TextChannel) -> bool:
        """Whether the bot has manage webhooks permission in the channel."""
        if isinstance(channel, (discord.threads.Thread, discord.PartialMessageable)):
            return False
        return channel.permissions_for(channel.guild.me).manage_webhooks

    async def prep_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Prepare a webhook, either from the cache or creating one. Raises WebhookError."""
        try:
            return await self.webhook_cache.prep_webhook(channel)
        except discord.Forbidden:
            raise inconnu.errors.WebhookError(
                "Inconnu needs `Manage Webhook` permission for this command."
            )
        except AttributeError:
            raise inconnu.errors.WebhookError("This feature isn't available in threads.")

    async def _set_presence(self):
        """Set the bot's presence message."""
        servers = len(self.guilds)
        message = f"/help | {servers} chronicles"

        logger.info("BOT: Setting presence")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=message)
        )

    async def mark_premium_loss(self, member: discord.Member, transferral=False):
        """Mark premium loss in the database."""
        await inconnu.db.supporters.update_one(
            {"_id": member.id},
            {"$set": {"_id": member.id, "discontinued": discord.utils.utcnow()}},
            upsert=True,
        )
        if transferral:
            await self.inform_premium_loss(
                member,
                "A premium character was just transferred to you, but you aren't a supporter",
            )
        else:
            await self.inform_premium_loss(member)

    async def mark_premium_gain(self, member: discord.Member):
        """Mark premium gain in the database."""
        await inconnu.db.supporters.update_one(
            {"_id": member.id},
            {"$set": {"_id": member.id, "discontinued": None}},
            upsert=True,
        )
        await self.inform_premium_features(member)

    async def transfer_premium(self, member: discord.Member, character: "VChar"):
        """
        When a character is transferred to a new user, mark that user's premium
        status if the character has images.
        """
        if not character.profile.images:
            logger.info("TRANSFER: {} has no images", character.name)
            return

        if not await inconnu.db.supporters.find_one({"_id": character.user}):
            logger.info(
                "TRANSFER: Creating a supporter record for {}, because {} has images",
                member.name,
                character.name,
            )
            await self.mark_premium_loss(member, True)
        else:
            logger.info("TRANSFER: {} has a supporter record; no action needed", member.name)

    # Events

    async def on_interaction(self, interaction: discord.Interaction):
        """Check whether the bot is ready before allowing the interaction to go through."""
        if not inconnu.emojis.loaded:
            # To speed up start times, we load emojis here rather than in on_ready
            await inconnu.emojis.load(bot)

        if interaction.type == discord.InteractionType.application_command:
            # Insert the raw interaction data in case we get a crash before
            # on_application_command() can perform its own insert. This creates
            # duplicate data; in the future, these routines will be merged.
            inter_data = {
                "guild": interaction.guild_id,
                "user": interaction.user.id if interaction.user else None,
            }
            inter_data.update(interaction.data)
            await inconnu.db.interactions.insert_one(inter_data)

        await self.process_application_commands(interaction)

    async def on_application_command(self, ctx: discord.ApplicationContext):
        """General processing after application commands."""
        # If a user specifies a character but only has one, we want to inform
        # them it's unnecessary so they don't keep doing it.
        options = inconnu.utils.raw_command_options(ctx.interaction)
        if "character" in options and "player" not in options:
            # Some commands do, in fact, need the character parameter
            if ctx.command.qualified_name not in {
                "character bio edit",
                "character delete",
                "experience remove entry",
                "experience award",
                "experience deduct",
                "update header",
                "transfer",
            }:
                num_chars = await inconnu.char_mgr.character_count(ctx.guild_id, ctx.user.id)
                if num_chars == 1:
                    # The user might have been using an SPC, so let's grab that
                    # character and double-check before yelling at them.
                    try:
                        character = await inconnu.char_mgr.fetchone(
                            ctx.guild, ctx.user, options["character"]
                        )
                        if character.is_pc:
                            await asyncio.sleep(1)  # Make sure it shows after the command
                            tip = (
                                "**Tip:** You only have one character, so you don't need "
                                f"the `character` option for `/{ctx.command.qualified_name}`."
                            )
                            await inconnu.utils.cmd_replace(ctx, tip, ephemeral=True)

                    except inconnu.errors.CharacterNotFoundError:
                        # They tried to look up a character they don't have
                        pass

        if self.motd and ctx.command.qualified_name not in {"motd", "announce"}:
            try:
                if ctx.user.id not in self.motd_given:
                    logger.debug("MOTD: Showing MOTD to {}", ctx.user.name)
                    await asyncio.sleep(1)
                    await inconnu.utils.cmd_replace(ctx, embed=self.motd, ephemeral=True)
                    self.motd_given.add(ctx.user.id)
            except discord.HTTPException:
                logger.warning("Could not show MotD to {}", ctx.user.name)

    async def on_connect(self):
        """Perform early setup."""
        if not self.connected:
            inconnu.char_mgr.bot = self
            await reporter.prepare_channel(self)
            self.webhook_cache = inconnu.webhookcache.WebhookCache(self.user.id)

            logger.info("CONNECT: Logged in as {}!", str(self.user))
            logger.info("CONNECT: Playing on {} servers", len(self.guilds))
            logger.info("CONNECT: {}", discord.version_info)
            logger.info("CONNECT: Latency: {} ms", self.latency * 1000)

            inconnu.models.VChar.SPC_OWNER = self.user.id
            logger.info("CONNECT: Registered SPC owner")

            self.connected = True
            await inconnu.db.init()

        await self.sync_commands()
        logger.info("CONNECT: Commands synced")

    async def on_ready(self):
        """Schedule a task to perform final setup."""
        await bot.wait_until_ready()
        if not bot.welcomed:
            logger.info("BOT: Internal cache built")

            server_info = await inconnu.db.server_info()
            logger.info(
                "MONGO: Version {}, using {} database",
                server_info["version"],
                server_info["database"],
            )

            # Schedule tasks
            cull_inactive.start()
            check_premium_expiries.start()

            self.welcomed = True

        # We always want to do these regardless of welcoming or not
        await self._set_presence()
        logger.info("BOT: Ready")

    @staticmethod
    async def on_application_command_error(context, exception):
        """Use centralized reporter to handle errors."""
        await reporter.report_error(context, exception)

    # Member Events

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Check for supporter status changes."""
        if before.guild.id != SUPPORTER_GUILD:
            return

        def is_supporter(member: discord.Member) -> bool:
            """Check if the member is a supporter."""
            return member.get_role(SUPPORTER_ROLE) is not None

        if is_supporter(before) and not is_supporter(after):
            logger.info("PREMIUM: {} is no longer a supporter", after.name)
            await self.mark_premium_loss(after)

        elif is_supporter(after) and not is_supporter(before):
            logger.info("PREMIUM: {} is now a supporter!", after.name)
            await self.mark_premium_gain(after)

    @staticmethod
    async def on_member_remove(member: discord.Member):
        """Mark all of a member's characters as inactive."""
        await inconnu.char_mgr.mark_inactive(member)

        if member.guild.id == SUPPORTER_GUILD:
            if member.get_role(SUPPORTER_ROLE):
                await bot.mark_premium_loss(member)

    @staticmethod
    async def on_member_join(member: discord.Member):
        """Mark all the player's characters as active when they rejoin a guild."""
        await inconnu.char_mgr.mark_active(member)

        if member.guild.id == SUPPORTER_GUILD:
            if member.get_role(SUPPORTER_ROLE):
                await bot.mark_premium_gain(member)

    # Guild Events

    async def on_guild_join(self, guild: discord.Guild):
        """Log whenever a guild is joined."""
        logger.info("BOT: Joined {}!", guild.name)
        await asyncio.gather(inconnu.stats.guild_joined(guild), self._set_presence())

    async def on_guild_remove(self, guild: discord.Guild):
        """Log guild removals."""
        logger.info("BOT: Left {} :(", guild.name)
        await asyncio.gather(inconnu.stats.guild_left(guild.id), self._set_presence())

    @staticmethod
    async def on_guild_update(before: discord.Guild, after: discord.Guild):
        """Log guild name changes."""
        if before.name != after.name:
            logger.info("BOT: Renamed {} => {}", before.name, after.name)
            await inconnu.stats.guild_renamed(after.id, after.name)

    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Update the webhooks cache."""
        await self.webhook_cache.update_webhooks(channel)


# Tasks


@tasks.loop(time=time(12, 0, tzinfo=timezone.utc))
async def cull_inactive():
    """Cull inactive characters and guilds."""
    await inconnu.tasks.cull()


@tasks.loop(time=time(0, tzinfo=timezone.utc))
async def check_premium_expiries():
    """Perform required actions on expired premium users."""
    await inconnu.tasks.premium.remove_expired_images()


# Set up the bot instance
intents = discord.Intents(guilds=True, members=True, messages=True, webhooks=True)
bot = InconnuBot(intents=intents, debug_guilds=DEBUG_GUILDS)
inconnu.bot = bot
