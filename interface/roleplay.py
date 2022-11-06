"""Roleplay commands."""
# pylint: disable=no-self-use

import os

import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from pymongo import UpdateOne

import inconnu
import interface
from logger import Logger

TEST_GUILDS = [int(os.environ["TEST_SERVER"])]


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
        mentions: Option(str, "Users, roles, and channels to mention", default=""),
    ):
        """Make an RP post as your character. Uses your current header."""
        await inconnu.roleplay.post(ctx, character, mentions=mentions)

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
        updates = interface.raw_bulk_delete_handler(
            payload,
            self.bot,
            lambda id: UpdateOne({"message_id": id}, {"$set": {"deleted": True}}),
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )
        if updates:
            Logger.debug("POST: Marking %s potential RP posts as deleted", len(updates))
            await inconnu.db.rp_posts.bulk_write(updates)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Set RP post deletion marker."""

        async def deletion_handler(message_id: int):
            """Mark an RP post as deleted."""
            Logger.debug("POST: Marking potential RP post as deleted")
            await inconnu.db.rp_posts.update_one(
                {"message_id": message_id}, {"$set": {"deleted": True}}
            )

        await interface.raw_message_delete_handler(
            raw_message,
            self.bot,
            deletion_handler,
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark RP posts deleted in the deleted channel."""
        Logger.info("POST: Marking all RP posts in %s as deleted", channel.name)
        await inconnu.db.rp_posts.update_many({"channel": channel.id}, {"$set": {"deleted": True}})


def setup(bot):
    """Set up the cog."""
    bot.add_cog(RoleplayCog(bot))
