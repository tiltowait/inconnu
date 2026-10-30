"""Supporter (premium) status tracking."""

from datetime import datetime

import discord
from loguru import logger

import constants
import db
from config import settings
from models import VChar
from utils.urls import docs_url


def is_supporter(member: discord.Member) -> bool:
    """Whether the member has the supporter role."""
    return member.get_role(settings.supporter_role) is not None


async def mark_lost(member: discord.Member):
    """Record that the member lost premium and DM them."""
    await _record(member, discord.utils.utcnow())
    await _inform_loss(member, "You are no longer a supporter!")


async def mark_gained(member: discord.Member, upload_mention: str | None):
    """Record that the member gained premium and DM them."""
    await _record(member, None)
    await _inform_features(member, upload_mention)


async def check_transfer(member: discord.Member, character: VChar):
    """Mark the new owner of a character with images as a lapsed supporter."""
    if not character.profile.images:
        logger.info("{} has no images; no premium transfer needed", character.name)
        return

    if await db.supporters.find_one({"_id": member.id}):
        logger.info("{} has a supporter record; no action needed", member.name)
        return

    logger.info(
        "Creating a supporter record for {}, because {} has images",
        member.name,
        character.name,
    )
    await _record(member, discord.utils.utcnow())
    await _inform_loss(
        member,
        "A premium character was just transferred to you, but you aren't a supporter",
    )


async def _record(member: discord.Member, discontinued: datetime | None):
    """Upsert the member's supporter record."""
    await db.supporters.update_one(
        {"_id": member.id},
        {"$set": {"_id": member.id, "discontinued": discontinued}},
        upsert=True,
    )


async def _inform_loss(member: discord.Member, title: str):
    """DM the member that their images will be deleted unless they resubscribe."""
    server = f"[Inconnu server]({constants.SUPPORT_URL})"
    patreon = f"[patron]({constants.PATREON})"
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

    try:
        await member.send(embed=embed)
        logger.info("Informed {} about premium loss", member.name)
    except discord.HTTPException:
        logger.info("Could not DM {} about premium loss", member.name)


async def _inform_features(member: discord.Member, upload_mention: str | None):
    """DM the member about the premium features they can now use."""
    embed = discord.Embed(
        title="Thank you for your support!",
        description=(
            f"You may now upload profile images via {upload_mention}. "
            "(Use it in a server, not from this DM!)\n\n"
            f"[Read more here!]({docs_url('premium/character-images')})"
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
