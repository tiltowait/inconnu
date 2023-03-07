"""Roleplay commands."""
# pylint: disable=no-self-use

import os
from datetime import timezone

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
    @commands.guild_only()
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
    @option("content", description="What to search for", default="")
    @option("mentioning", description="A user mentioned in the post", required=False)
    @option(
        "hidden",
        description="Whether to hide the search results from others (default true)",
        default=True,
    )
    @option(
        "summary",
        description="Whether to show a summary instead of full posts (default false)",
        default=False,
    )
    @commands.guild_only()
    async def search(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        content: str,
        mentioning: discord.Member,
        hidden: bool,
        summary: bool,
    ):
        """Search for an RP post. Displays up to 5 results."""
        await inconnu.roleplay.search(ctx, user, content, mentioning, hidden, summary)

    @slash_command(guild_ids=TEST_GUILDS)
    @commands.guild_only()
    async def tags(self, ctx: discord.ApplicationContext):
        """View your RP posts by tag."""
        await inconnu.roleplay.tags.show_tags(ctx)

    # Message commands

    @slash_command(guild_ids=TEST_GUILDS)
    @commands.guild_only()
    async def bookmarks(self, ctx: discord.ApplicationContext):
        """View your RP post bookmarks."""
        await inconnu.roleplay.show_bookmarks(ctx)

    @commands.message_command(name="Post: Edit", guild_ids=TEST_GUILDS)
    @commands.guild_only()
    async def edit_rp_post(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Edit the selected roleplay post."""
        await inconnu.roleplay.edit_post(ctx, message)

    @commands.message_command(name="Post: Delete", guild_ids=TEST_GUILDS)
    @commands.guild_only()
    async def delete_rp_post(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Delete the selected roleplay post."""
        await inconnu.roleplay.delete_message_chain(ctx, message)

    # Listeners

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk mark RP posts as deleted."""
        updates = interface.raw_bulk_delete_handler(
            payload,
            self.bot,
            lambda id: UpdateOne(
                {"message_id": id},
                {"$set": {"deleted": True, "deletion_date": discord.utils.utcnow()}},
            ),
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )
        if updates:
            Logger.debug("POST: Marking %s potential RP posts as deleted", len(updates))
            await inconnu.db.rp_posts.bulk_write(updates)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Mark an RP post as deleted and post a notice in the guild's deletion
        channel."""
        if (message := raw_message.cached_message) is not None:
            if not message.author.bot:
                return
            if message.flags.ephemeral:
                return

        # We can't rely on ensuring there's a webhook, so we fetch if it's a
        # bot message or a message not in the cache. Hopefully it isn't too
        # expensive ...
        post = await inconnu.db.rp_posts.find_one_and_update(
            {"message_id": raw_message.message_id},
            {"$set": {"deleted": True, "deletion_date": discord.utils.utcnow()}},
        )
        if post is not None:
            Logger.debug("POST: Marked RP post as deleted")
            deletion_id = await inconnu.settings.deletion_channel(post["guild"])
            if deletion_id:
                channel = self.bot.get_partial_messageable(deletion_id)

                embed = discord.Embed(
                    title="Post Deleted",
                    description=(
                        f"**Poster:** <@{post['user']}>\n"
                        f"**Channel:** <#{post['channel']}>\n"
                        "**Content:**\n\n" + post["content"]
                    ),
                    url=inconnu.post_url(post["_id"]),
                    color=discord.Color.red(),
                )
                embed.timestamp = post["date"].replace(tzinfo=timezone.utc)

                try:
                    await channel.send(embed=embed)
                    Logger.info(
                        "POST: Sent deletion notice to deletion at %s: %s",
                        post["guild"],
                        deletion_id,
                    )
                except discord.Forbidden:
                    Logger.info(
                        "POST: Unable to send deletion notice to %s: %s (Missing permissions)",
                        post["guild"],
                        deletion_id,
                    )
                except discord.HTTPException:
                    Logger.info(
                        "POST: Unable to send deletion notice to %s: %s (Channel not found)",
                        post["guild"],
                        deletion_id,
                    )
            else:
                Logger.debug("POST: No deletion channel set on %s", post["guild"])
        else:
            Logger.debug("POST: Deleted message is not an RP post")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark RP posts deleted in the deleted channel."""
        Logger.info("POST: Marking all RP posts in %s as deleted", channel.name)
        await inconnu.db.rp_posts.update_many(
            {"channel": channel.id},
            {"$set": {"deleted": True, "deletion_date": discord.utils.utcnow()}},
        )


def setup(bot):
    """Set up the cog."""
    bot.add_cog(RoleplayCog(bot))
