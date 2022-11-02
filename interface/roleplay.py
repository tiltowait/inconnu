"""Roleplay commands."""
# pylint: disable=no-self-use

import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from pymongo import UpdateOne

import inconnu
from logger import Logger

TEST_GUILDS = [676333549720174605, 826628660450689074]  # CtBN and dev server


class RoleplayCog(commands.Cog):
    """A cog with roleplay commands."""

    def __init__(self, bot):
        self.bot = bot

    # Slash commands

    @slash_command(guild_ids=TEST_GUILDS)
    async def post(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to post as", required=True),
        mention: Option(discord.Member, "The player to mention", required=False),
    ):
        """Make an RP post as your character. Uses your current header."""
        await inconnu.roleplay.post(ctx, character, mention=mention)

    @slash_command(guild_ids=TEST_GUILDS)
    async def search(
        self,
        ctx: discord.ApplicationContext,
        user: Option(discord.Member, "The user who made the post"),
        content: Option(str, "What to search for"),
    ):
        """Search for an RP post. Displays up to 5 results."""
        await inconnu.roleplay.search(ctx, user, content)

    # Message commands

    @commands.message_command(name="Edit RP Post", guild_ids=TEST_GUILDS)
    @commands.guild_only()
    async def edit_rp_post(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Edit the selected roleplay post."""
        await inconnu.roleplay.edit_post(ctx, message)

    # Listeners

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk mark RP posts as deleted."""
        raw_ids = payload.message_ids
        updates = []

        for message in payload.cached_messages:
            raw_ids.discard(message.id)
            if message.author == self.bot.user:
                Logger.debug("POST: Adding potential RP post to update queue")
                updates.append(UpdateOne({"message_id": message.id}, {"$set": {"deleted": True}}))

        for message_id in raw_ids:
            Logger.debug("POST: Blindly adding potential RP post to update queue")
            updates.append(UpdateOne({"message_id": message_id}, {"$set": {"deleted": True}}))

        Logger.debug("POST: Marking %s potential RP posts as deleted", len(updates))
        await inconnu.db.rp_posts.bulk_write(updates)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Set RP post deletion marker."""
        # We only have a raw message event, which may not be in the message
        # cache. If it isn't, then we just have to blindly attempt to update
        # the record. If this proves to be a performance hit, we'll have to
        # revert to using on_message_delete().
        if (message := raw_message.cached_message) is not None:
            # Got a cached message, so we can be a little more efficient and
            # only call the database if it belongs to the bot
            if message.author == self.bot.user:
                Logger.debug("POST: Marking potential RP post as deleted")
                await inconnu.db.rp_posts.update_one(
                    {"message_id": message.id}, {"$set": {"deleted": True}}
                )
        else:
            # The message isn't in the cache; blindly delete the record
            # if it exists
            Logger.debug("POST: Blindly marking potential RP post as deleted")
            await inconnu.db.rp_posts.update_one(
                {"message_id": raw_message.message_id}, {"$set": {"deleted": True}}
            )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark RP posts deleted in the deleted channel."""
        Logger.info("POST: Marking all RP posts in %s as deleted", channel.name)
        await inconnu.db.rp_posts.update_many({"channel": channel.id}, {"$set": {"deleted": True}})


def setup(bot):
    """Set up the cog."""
    bot.add_cog(RoleplayCog(bot))
