"""Tasks for premium features."""

import asyncio
from datetime import timedelta

import discord

import inconnu
import s3
from logger import Logger


async def remove_expired_images():
    """Removes images from expired premium users."""
    Logger.info("TASK: Removing images from expired supporters")

    expiration = discord.utils.utcnow() - timedelta(days=7)
    expired_user_ids = []
    s3_tasks = []
    async for supporter in inconnu.db.supporters.find({"discontinued": {"$lt": expiration}}):
        user_id = supporter["_id"]
        expired_user_ids.append(user_id)
        Logger.info("TASK: Removing %s's profile images", user_id)

        # The cache doesn't have a facility for fetching cross-guild, so we
        # have to fetch them manually
        async for character in inconnu.models.VChar.find({"user": user_id}):
            if character.profile.images:
                s3_tasks.append(s3.delete_character_images(character))

    Logger.info(
        "TASK: Removing images from %s characters due to expired supporter status",
        len(s3_tasks),
    )
    if s3_tasks:
        # We have to do the S3 tasks first, because the character tasks will
        # erase all record of the image URLs

        # Because we directly modified the database, we have to purge the cache
        inconnu.char_mgr.purge()

        await asyncio.gather(*s3_tasks)
        await inconnu.db.supporters.delete_many({"_id": {"$in": expired_user_ids}})

        # There is a very rare but potential race condition: a former supporter
        # might have loaded their character between purge begin and end.
        # Ideally, we would do all this in the cache; failing that, we would
        # somehow lock the cache until this task is complete. Until a better
        # solution is found, we try to hedge our bets by purging the cache once
        # more.
        inconnu.char_mgr.purge()
