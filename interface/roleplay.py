"""Roleplay commands."""
# pylint: disable=no-self-use

import os

import discord
from discord import option
from discord.commands import OptionChoice, slash_command
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
    @inconnu.options.char_option("The character to post as")
    @option("mentions", description="Users, roles, and channels to mention", default="")
    @option(
        "blush",
        description="THIS POST ONLY: Is Blush of Life active?",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0), OptionChoice("N/A", -1)],
        required=False,
    )
    @option(
        "hunger",
        description="THIS POST ONLY: The character's Hunger (vampires only)",
        choices=[i for i in range(6)],
        required=False,
    )
    @option(
        "location", description="THIS POST ONLY: Where the scene is taking place", required=False
    )
    @option("merits", description="THIS POST ONLY: Obvious/important merits", required=False)
    @option("flaws", description="THIS POST ONLY: Obvious/important flaws", required=False)
    @option("temporary", descroption="THIS POST ONLY: Temporary effects", required=False)
    @option(
        "display_header",
        description="Display a header above the post (default true)",
        default=True,
    )
    @inconnu.utils.has_premium()
    async def post(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        mentions: str,
        blush: int,
        hunger: int,
        location: str,
        merits: str,
        flaws: str,
        temporary: str,
        display_header: bool,
    ):
        """Make an RP post as your character. Uses your current header."""
        await inconnu.roleplay.post(
            ctx,
            character,
            mentions=mentions,
            blush=blush,
            hunger=hunger,
            location=location,
            merits=merits,
            flaws=flaws,
            temp=temporary,
            show_header=display_header,
        )

    @slash_command(guild_ids=TEST_GUILDS)
    @option("user", description="The user who wrote the post")
    @option("content", description="What to search for")
    @option(
        "hidden",
        description="Whether to hide the search results from others (default true)",
        default=True,
    )
    async def search(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        content: str,
        hidden: bool,
    ):
        """Search for an RP post. Displays up to 5 results."""
        await inconnu.roleplay.search(ctx, user, content, hidden)

    # Message commands

    @slash_command(guild_ids=TEST_GUILDS)
    async def bookmarks(self, ctx: discord.ApplicationContext):
        """View your RP post bookmarks."""
        await inconnu.roleplay.show_bookmarks(ctx)

    @commands.message_command(name="Post: Edit", guild_ids=TEST_GUILDS)
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
