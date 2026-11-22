"""Supporter (premium) status tracking."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import discord
from loguru import logger

import constants
import db
from config import settings
from utils.text import pluralize
from utils.urls import docs_url

if TYPE_CHECKING:
    from bot import InconnuBot

# How long lapsed supporters keep their images
GRACE_PERIOD = timedelta(days=7)

# Current supporters' user IDs, so checks needn't wait for the member cache
_supporters: set[int] = set()

# Users whose status changed while sync() runs, which it leaves alone
_changed_during_sync: set[int] | None = None


def is_supporter(user_id: int) -> bool:
    """Whether the user is a supporter."""
    return user_id in _supporters


async def initialize():
    """Load the supporters from the database."""
    _supporters.clear()
    async for record in db.supporters.find({"discontinued": None}, {"_id": 1}):
        _supporters.add(record["_id"])
    logger.info("Loaded {} supporters", len(_supporters))


async def sync(bot: discord.Client):
    """Bring supporter status up to date with the support server's members,
    catching changes made while the bot was offline. Nobody is DMed.

    The support server is fetched rather than taken from the cache, which may
    not have its roles yet. Without them, everyone would look like a
    non-supporter."""
    global _changed_during_sync
    _changed_during_sync = set()
    try:
        guild = await bot.fetch_guild(settings.supporter_guild)
        if guild.get_role(settings.supporter_role) is None:
            logger.error("The support server has no supporter role; skipping the sync")
            return

        current = {
            m.id
            async for m in guild.fetch_members(limit=None)
            if m.get_role(settings.supporter_role)
        }
        gained = current - _supporters
        lost = _supporters - current

        now = discord.utils.utcnow()
        # A role change seen since the fetch is newer than it
        gained -= _changed_during_sync
        lost -= _changed_during_sync

        changes = [(uid, None) for uid in gained] + [(uid, now) for uid in lost]
        applied = {True: 0, False: 0}
        for user_id, discontinued in changes:
            # Or one seen during an earlier write
            if user_id not in _changed_during_sync:
                await _set_status(user_id, discontinued)
                applied[discontinued is None] += 1

        logger.info("Supporter sync: {} gained, {} lost", applied[True], applied[False])
    finally:
        _changed_during_sync = None


async def mark_lost(user: discord.Member | discord.User):
    """Record that the user lost premium and DM them."""
    await _set_status(user.id, discord.utils.utcnow())
    await _inform_loss(user, "You are no longer a supporter!")


async def mark_gained(member: discord.Member, bot: InconnuBot):
    """Record that the member gained premium and DM them."""
    await _set_status(member.id, None)
    await _inform_features(member, bot)


async def lapse_date(user_id: int) -> datetime | None:
    """When the user's premium lapsed, for timing image deletion. None for
    supporters. Non-supporters without a lapsed record are marked as lapsed
    now, giving them the full grace period. Lapsed supporters keep their
    existing date, so transfers can't extend it.

    NOTE: This races with recording a role gain (by sync() or a member event).
    If the gain lands during find_one() or _record(), this overwrites it with a
    lapsed record while the set still says supporter. Unless the bot restarts
    (whose sync repairs the record) within GRACE_PERIOD, the images are then
    deleted. It needs a transfer of a character with images within milliseconds
    of the new owner's role gain, so we accept the risk."""
    if is_supporter(user_id):
        return None

    record = await db.supporters.find_one({"_id": user_id})
    if record is None or record["discontinued"] is None:
        # Never was a supporter, or their record is somehow stale
        logger.info("Marking {} as lapsed", user_id)
        discontinued = discord.utils.utcnow()
        await _record(user_id, discontinued)
        return discontinued

    discontinued = record["discontinued"]
    if discontinued.tzinfo is None:
        # Mongo returns naive UTC datetimes
        discontinued = discontinued.replace(tzinfo=UTC)
    return discontinued


async def _set_status(user_id: int, discontinued: datetime | None):
    """Record the user's status and update the supporter set. Supporters
    have no discontinuation date.

    The set changes before the write, so another event for the user that
    arrives during it sees the new status and doesn't repeat the change."""
    if discontinued is None:
        _supporters.add(user_id)
    else:
        _supporters.discard(user_id)
    if _changed_during_sync is not None:
        _changed_during_sync.add(user_id)
    await _record(user_id, discontinued)


async def _record(user_id: int, discontinued: datetime | None):
    """Upsert the user's supporter record."""
    await db.supporters.update_one(
        {"_id": user_id},
        {"$set": {"_id": user_id, "discontinued": discontinued}},
        upsert=True,
    )


async def _inform_loss(member: discord.Member | discord.User, title: str):
    """DM the user that their images will be deleted unless they resubscribe."""
    server = f"[Inconnu server]({constants.SUPPORT_URL})"
    patreon = f"[patron]({constants.PATREON})"
    embed = discord.Embed(
        title=title,
        description=(
            f"If you aren't a {patreon} within {pluralize(GRACE_PERIOD.days, 'day')}, your "
            "character profile images will be deleted.\n\n"
            f"To maintain supporter status, you must be on the {server} "
            f"and a {patreon}.\n\n"
            "**Note:** Old-style (URL-based) images are grandfathered "
            "in and will not be removed."
        ),
        color=discord.Color.red(),
    )
    embed.set_footer(text="Thank you for your support!")

    try:
        await member.send(embed=embed)
        logger.info("Informed {} about premium loss", member.name)
    except discord.HTTPException:
        logger.info("Could not DM {} about premium loss", member.name)


async def _inform_features(member: discord.Member, bot: InconnuBot):
    """DM the member about the premium features they can now use."""

    def mention(name: str) -> str:
        """The command's mention, or its name if it can't be found."""
        return bot.cmd_mention(name) or f"`/{name}`"

    features = [
        f"Add [character images]({docs_url('premium/character-images')}) with "
        + mention("character image upload"),
        f"Post as your characters with [Roleposting]({docs_url('premium/roleposting')}) "
        + f"using {mention('post')}",
        f"Choose an [emoji theme]({docs_url('advanced/server-settings#emoji-theme')}) "
        + f"in {mention('settings')}",
        f"Edit and play your characters in the [web app]({docs_url('premium/web-app')})",
    ]
    embed = discord.Embed(
        title="Thank you for your support!",
        description=(
            "You can now:\n"
            + "\n".join(f"- {feature}" for feature in features)
            + "\n\nUse commands in a server, not this DM."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(
        text=(
            "You are responsible for the images you upload. "
            "Violating the terms of service will result in a permanent ban from the bot."
        )
    )

    try:
        await member.send(embed=embed)
        logger.info("Informed {} about premium features", member.name)
    except discord.HTTPException:
        logger.info("Could not DM {} about premium features", member.name)
