"""Tasks for premium features."""

import asyncio
from datetime import timedelta

import discord

import api
import inconnu
from logger import Logger


async def remove_expired_images():
    """Removes images from expired premium users."""
    Logger.info("TASK: Removing images from expired supporters")

    expiration = discord.utils.utcnow() - timedelta(days=7)
    expired_user_ids = []
    api_tasks = []
    async for supporter in inconnu.db.supporters.find({"discontinued": {"$lt": expiration}}):
        user_id = supporter["_id"]
        expired_user_ids.append(user_id)
        Logger.info("TASK: Removing %s's profile images", user_id)

        # The cache doesn't have a facility for fetching cross-guild, so we
        # have to fetch them manually
        async for character in inconnu.models.VChar.find({"user": user_id}):
            Logger.info("TASK: Removing images from %s", character.name)
            api_tasks.append(api.delete_character_faceclaims(character))

    Logger.info(
        "TASK: Removing images from %s characters due to expired supporter status",
        len(api_tasks),
    )
    if api_tasks:
        await asyncio.gather(*api_tasks)
    if expired_user_ids:
        await inconnu.db.supporters.delete_many({"_id": {"$in": expired_user_ids}})
