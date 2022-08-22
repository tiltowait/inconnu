"""Bot instance and event handlers."""

import asyncio
import os
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        self.ready = False
        self.welcomed = False
        self.lockdown = None
        self.wizards = 0
        self.motd = None
        self.motd_given = set()
        Logger.info("BOT: Instantiated")

    def set_motd(self, embed: discord.Embed | None):
        """Set the MOTD embed."""
        self.motd = embed
        self.motd_given = set()

    async def inform_premium_loss(self, member: discord.Member):
        """Inform a member if they lost premium status."""
        try:
            server = f"[Inconnu server]({inconnu.constants.SUPPORT_URL})"
            patreon = f"[patron]({inconnu.constants.PATREON})"
            embed = discord.Embed(
                title="You are no longer a supporter!",
                description=(
                    "If you do not re-up your membership within 7 days, "
                    "any profile images you've uploaded will be deleted.\n\n"
                    f"To maintain supporter status, you must be on the {server} "
                    f"and a {patreon}."
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text="Thank you for your support!")
            await member.send(embed=embed)

        except discord.errors.Forbidden:
            # Their DMs are closed, and there's nothing we can do about it
            pass

    async def inform_premium_features(self, member: discord.Member):
        """Inform the member of premium features."""
        try:
            embed = discord.Embed(
                title="Thank you for your support!",
                description="You may now upload profile images via `/character image upload`.",
                color=discord.Color.green(),
            )
            await member.send(embed=embed)

        except discord.errors.Forbidden:
            # Their DMs are closed
            pass

    async def get_or_fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Look up a guild in the guild cache or fetches if not found."""
        if guild := self.get_guild(guild_id):
            return guild
        Logger.debug("BOT: Guild %s not found in cache; attempting fetch", guild_id)
        return await self.fetch_guild(guild_id)

    async def on_interaction(self, interaction: discord.Interaction):
        """Check whether the bot is ready before allowing the interaction to go through."""
        if not self.ready:
            err = f"{self.user.mention} is currently restarting. This might take a few minutes."
            await inconnu.respond(interaction)(err, ephemeral=True)
        else:
            await self.process_application_commands(interaction)

    async def mark_premium_loss(self, member: discord.Member):
        """Mark premium loss in the database."""
        await inconnu.db.supporters.insert_one(
            {"_id": member.id, "timestamp": discord.utils.utcnow()}
        )
        await self.inform_premium_loss(member)

    async def mark_premium_gain(self, member: discord.Member):
        """Mark premium gain in the database."""
        await inconnu.db.supporters.delete_one({"_id": member.id})
        await self.inform_premium_features(member)

    # Events

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
                num_chars = await inconnu.char_mgr.character_count(ctx.guild.id, ctx.user.id)
                if num_chars == 1:
                    # The user might have been using an SPC, so let's grab that
                    # character and double-check before yelling at them.
                    character = await inconnu.char_mgr.fetchone(
                        ctx.guild, ctx.user, options["character"]
                    )
                    if character.is_pc:
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

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Check for supporter status changes."""
        if before.guild.id != SUPPORTER_GUILD:
            return

        def is_supporter(member: discord.Member) -> bool:
            """Check if the member is a supporter."""
            return member.get_role(SUPPORTER_ROLE) is not None

        if is_supporter(before) and not is_supporter(after):
            Logger.info("BOT: %s#%s is no longer a supporter", after.name, after.discriminator)
            await self.mark_premium_loss(after)

        elif is_supporter(after) and not is_supporter(before):
            Logger.info("BOT: %s#%s is now a supporter!", after.name, after.discriminator)
            await self.mark_premium_gain(after)


# Set up the bot instance
intents = discord.Intents(guilds=True, members=True, messages=True)
bot = InconnuBot(intents=intents, debug_guilds=DEBUG_GUILDS)

# General Events


@bot.event
async def on_ready():
    """Schedule a task to perform final setup."""
    await inconnu.emojis.load(bot)
    bot.ready = True
    Logger.info("BOT: Accepting commands")

    await bot.wait_until_ready()
    if not bot.welcomed:
        Logger.info("BOT: Internal cache built")
        Logger.info("BOT: Logged in as %s!", str(bot.user))
        Logger.info("BOT: Playing on %s servers", len(bot.guilds))
        Logger.info("BOT: %s", discord.version_info)
        Logger.info("BOT: Latency: %s ms", bot.latency * 1000)

        server_info = await inconnu.db.server_info()
        database = os.environ["MONGO_DB"]
        Logger.info("MONGO: Version %s, using %s database", server_info["version"], database)

        # Schedule tasks
        cull_inactive.start()
        upload_logs.start()
        check_premium_expiries.start()

        # Final prep
        inconnu.char_mgr.bot = bot
        reporter.prepare_channel(bot)
        bot.welcomed = True

    # We always want to do these regardless of welcoming or not
    await __set_presence()
    Logger.info("BOT: Ready")


@bot.event
async def on_application_command_error(ctx, error):
    """Use centralized reporter to handle errors."""
    await reporter.report_error(ctx, error)


# Member Events


@bot.event
async def on_member_remove(member):
    """Mark all of a member's characters as inactive."""
    await inconnu.char_mgr.mark_inactive(member)

    if member.guild.id == SUPPORTER_GUILD:
        if member.get_role(SUPPORTER_ROLE):
            await bot.mark_premium_loss(member)


@bot.event
async def on_member_join(member):
    """Mark all the player's characters as active when they rejoin a guild."""
    await inconnu.char_mgr.mark_active(member)

    if member.guild.id == SUPPORTER_GUILD:
        if member.get_role(SUPPORTER_ROLE):
            await bot.mark_premium_gain(member)


# Guild Events


@bot.event
async def on_guild_join(guild):
    """Log whenever a guild is joined."""
    Logger.info("BOT: Joined %s!", guild.name)
    await asyncio.gather(inconnu.stats.guild_joined(guild), __set_presence())


@bot.event
async def on_guild_remove(guild):
    """Log guild removals."""
    Logger.info("BOT: Left %s :(", guild.name)
    await asyncio.gather(inconnu.stats.guild_left(guild.id), __set_presence())


@bot.event
async def on_guild_update(before, after):
    """Log guild name changes."""
    if before.name != after.name:
        Logger.info("BOT: Renamed %s => %s", before.name, after.name)
        await inconnu.stats.guild_renamed(after.id, after.name)


# Tasks


@tasks.loop(time=time(12, 0, tzinfo=timezone.utc))
async def cull_inactive():
    """Cull inactive characters and guilds."""
    await inconnu.culler.cull()


@tasks.loop(time=time(12, 0, tzinfo=timezone.utc))
async def check_premium_expiries():
    """Perform required actions on expired premium users."""
    await inconnu.tasks.premium.remove_expired_images()


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


# Misc and helpers


async def __set_presence():
    """Set the bot's presence message."""
    servers = len(bot.guilds)
    message = f"/help | {servers} chronicles"

    Logger.info("BOT: Setting presence")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=message)
    )


def setup():
    """Add the cogs to the bot."""
    for filename in os.listdir("./interface"):
        if filename[0] != "_" and filename.endswith(".py"):
            Logger.debug("COGS: Loading %s", filename)
            bot.load_extension(f"interface.{filename[:-3]}", store=False)


async def run():
    """Set up and run the bot."""
    setup()
    try:
        await bot.start(os.environ["INCONNU_TOKEN"])
    except KeyboardInterrupt:
        Logger.info("BOT: Logging out")
        await bot.bot.logout()
