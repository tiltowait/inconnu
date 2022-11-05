"""Bot instance and event handlers."""

import asyncio
import os
from collections import defaultdict
from datetime import time, timezone

import discord
from discord.ext import tasks

import config.logging
import inconnu
import s3
from config import DEBUG_GUILDS, SUPPORTER_GUILD, SUPPORTER_ROLE
from errorreporter import reporter
from logger import Logger


class InconnuBot(discord.Bot):
    """Adds minor functionality over the superclass. All commands in cogs."""

    WEBHOOK_NAME = "Inconnuhook"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.ready = False
        self.welcomed = False
        self.lockdown = None
        self.wizards = 0
        self.motd = None
        self.motd_given = set()
        self.webhooks: dict[int, discord.Webhook] = defaultdict(lambda: None)
        Logger.info("BOT: Instantiated")

        # Add the cogs
        for filename in os.listdir("./interface"):
            if filename[0] != "_" and filename.endswith(".py"):
                Logger.debug("COGS: Loading %s", filename)
                self.load_extension(f"interface.{filename[:-3]}")

    def set_motd(self, embed: discord.Embed | None):
        """Set the MOTD embed."""
        self.motd = embed
        self.motd_given = set()

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
            Logger.info(
                "PREMIUM: Informed %s#%s about premium loss", member.name, member.discriminator
            )

        except discord.errors.Forbidden:
            Logger.info(
                "PREMIUM: Could not DM %s#%s about premium loss", member.name, member.discriminator
            )

    @staticmethod
    async def inform_premium_features(member: discord.Member):
        """Inform the member of premium features."""
        try:
            embed = discord.Embed(
                title="Thank you for your support!",
                description=(
                    "You may now upload profile images via `/character image upload`.\n\n"
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
            Logger.info(
                "PREMIUM: Informed %s#%s about premium features", member.name, member.discriminator
            )

        except discord.errors.Forbidden:
            Logger.info(
                "PREMIUM: Could not DM %s#%s about premium features",
                member.name,
                member.discriminator,
            )

    async def get_or_fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Look up a guild in the guild cache or fetches if not found."""
        if guild := self.get_guild(guild_id):
            return guild
        Logger.debug("BOT: Guild %s not found in cache; attempting fetch", guild_id)
        return await self.fetch_guild(guild_id)

    async def prep_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Prepare a webhook, either from the cache or creating one. Raises Forbidden."""
        if not self.webhooks[channel.id]:
            if (webhook := await self._find_webhook(channel)) is None:
                webhook = await channel.create_webhook(name="Inconnuhook", reason="For RP posts")
                Logger.info(
                    "WEBHOOK: Created a webhook in #%s on %s",
                    channel.name,
                    channel.guild.name,
                )
            # Add it to the cache
            self.webhooks[channel.id] = webhook
        else:
            Logger.info("WEBHOOK: Webhook CACHED in #%s on %s", channel.name, channel.guild.name)

        return self.webhooks[channel.id]

    async def _set_presence(self):
        """Set the bot's presence message."""
        servers = len(self.guilds)
        message = f"/help | {servers} chronicles"

        Logger.info("BOT: Setting presence")
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
            Logger.info("TRANSFER: %s has no images", character.name)
            return

        if not await inconnu.db.supporters.find_one({"_id": character.user}):
            Logger.info(
                "TRANSFER: Creating a supporter record for %s#%s, because %s has images",
                member.name,
                member.discriminator,
                character.name,
            )
            await self.mark_premium_loss(member, True)
        else:
            Logger.info(
                "TRANSFER: %s#%s has a supporter record; no action needed",
                member.name,
                member.discriminator,
            )

    # Events

    async def on_interaction(self, interaction: discord.Interaction):
        """Check whether the bot is ready before allowing the interaction to go through."""
        # It's better UX to allow autocomplete interactions to go through even
        # if the bot isn't ready; users frequently get confused if the menus
        # don't populate during restart.
        if self.ready or interaction.type == discord.InteractionType.auto_complete:
            await self.process_application_commands(interaction)
        else:
            err = f"{self.user.mention} is currently restarting. This might take a few minutes."
            await inconnu.respond(interaction)(err, ephemeral=True)

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
                "post",
                "update header",
                "transfer",
            }:
                num_chars = await inconnu.char_mgr.character_count(ctx.guild.id, ctx.user.id)
                if num_chars == 1:
                    # The user might have been using an SPC, so let's grab that
                    # character and double-check before yelling at them.
                    character = await inconnu.char_mgr.fetchone(
                        ctx.guild, ctx.user, options["character"]
                    )
                    if character.is_pc:
                        await asyncio.sleep(1)  # Make sure it shows after the command
                        await ctx.respond(
                            (
                                "**Tip:** You only have one character, so you don't need "
                                f"the `character` option for `/{ctx.command.qualified_name}`."
                            ),
                            ephemeral=True,
                        )

        if self.motd:
            if ctx.user.id not in self.motd_given:
                Logger.debug("MOTD: Showing MOTD to %s#%s", ctx.user.name, ctx.user.discriminator)
                await asyncio.sleep(1)
                await ctx.respond(embed=self.motd, ephemeral=True)
                self.motd_given.add(ctx.user.id)

    async def on_ready(self):
        """Schedule a task to perform final setup."""
        await inconnu.emojis.load(bot)
        self.ready = True
        Logger.info("BOT: Accepting commands")

        await bot.wait_until_ready()
        if not bot.welcomed:
            Logger.info("BOT: Internal cache built")
            Logger.info("BOT: Logged in as %s!", str(self.user))
            Logger.info("BOT: Playing on %s servers", len(self.guilds))
            Logger.info("BOT: %s", discord.version_info)
            Logger.info("BOT: Latency: %s ms", self.latency * 1000)

            server_info = await inconnu.db.server_info()
            Logger.info(
                "MONGO: Version %s, using %s database",
                server_info["version"],
                server_info["database"],
            )

            # Schedule tasks
            cull_inactive.start()
            upload_logs.start()
            check_premium_expiries.start()

            # Final prep
            inconnu.char_mgr.bot = self
            reporter.prepare_channel(self)
            self.welcomed = True

        # We always want to do these regardless of welcoming or not
        await self._set_presence()
        Logger.info("BOT: Ready")

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
            Logger.info("PREMIUM: %s#%s is no longer a supporter", after.name, after.discriminator)
            await self.mark_premium_loss(after)

        elif is_supporter(after) and not is_supporter(before):
            Logger.info("PREMIUM: %s#%s is now a supporter!", after.name, after.discriminator)
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
        Logger.info("BOT: Joined %s!", guild.name)
        await asyncio.gather(inconnu.stats.guild_joined(guild), self._set_presence())

    async def on_guild_remove(self, guild: discord.Guild):
        """Log guild removals."""
        Logger.info("BOT: Left %s :(", guild.name)
        await asyncio.gather(inconnu.stats.guild_left(guild.id), self._set_presence())

    @staticmethod
    async def on_guild_update(before: discord.Guild, after: discord.Guild):
        """Log guild name changes."""
        if before.name != after.name:
            Logger.info("BOT: Renamed %s => %s", before.name, after.name)
            await inconnu.stats.guild_renamed(after.id, after.name)

    async def _find_webhook(self, channel: discord.TextChannel):
        """Find the appropriate webhook in the channel."""
        for _webhook in await channel.webhooks():
            if _webhook.name == self.WEBHOOK_NAME:
                Logger.info(
                    "WEBHOOK: %s found in #%s on %s",
                    self.WEBHOOK_NAME,
                    channel.name,
                    channel.guild.name,
                )
                return _webhook

        Logger.info("WEBHOOK: Not found in #%s on %s", channel.name, channel.guild.name)
        return None

    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Update the webhooks cache."""
        # TODO: Prevent this API call when we just created the webhook
        self.webhooks[channel.id] = await self._find_webhook(channel)


# Tasks


@tasks.loop(time=time(12, 0, tzinfo=timezone.utc))
async def cull_inactive():
    """Cull inactive characters and guilds."""
    await inconnu.tasks.cull()


@tasks.loop(time=time(0, tzinfo=timezone.utc))
async def check_premium_expiries():
    """Perform required actions on expired premium users."""
    if discord.utils.utcnow().day == 1:
        # Only run task on the first day of the month
        await inconnu.tasks.premium.remove_expired_images()
    else:
        Logger.debug("TASK: Premium expiration checks only happen on the first of the month")


@tasks.loop(hours=1)
async def upload_logs():
    """Upload logs to S3."""
    if not config.logging.upload_to_aws:
        Logger.warning("TASK: Log uploading disabled. Unscheduling task")
        upload_logs.stop()
    elif not await s3.upload_logs():
        Logger.error("TASK: Unable to upload logs. Unscheduling task")
        upload_logs.stop()
    else:
        Logger.info("TASK: Logs uploaded")


# Set up the bot instance
intents = discord.Intents(guilds=True, members=True, messages=True, webhooks=True)
bot = InconnuBot(intents=intents, debug_guilds=DEBUG_GUILDS)
inconnu.bot = bot


async def run():
    """Set up and run the bot."""
    try:
        await bot.start(os.environ["INCONNU_TOKEN"])
    except KeyboardInterrupt:
        Logger.info("BOT: Logging out")
        await bot.bot.logout()
