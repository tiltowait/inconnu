"""Roleplay commands."""

from datetime import timezone

import discord
from discord import option
from discord.commands import OptionChoice, slash_command
from discord.ext import commands
from loguru import logger
from pymongo import UpdateOne

import db
import inconnu
import interface
import services
from utils.decorators import premium


class RoleplayCog(commands.Cog):
    """A cog with roleplay commands."""

    def __init__(self, bot):
        self.bot = bot

    # Slash commands

    @slash_command(contexts={discord.InteractionContextType.guild})
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
    @premium()
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
        """Make a Rolepost as your character. Uses your current header."""
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

    @slash_command(name="pmnh", contexts={discord.InteractionContextType.guild})
    @option("mentions", description="Users, roles, and channels to mention")
    @inconnu.options.char_option("The character to post as")
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
        description="Display a header above the post (default false)",
        default=False,
    )
    @premium()
    async def post_shortcut(
        self,
        ctx: discord.ApplicationContext,
        mentions: str,
        character: str,
        blush: int,
        hunger: int,
        location: str,
        merits: str,
        flaws: str,
        temporary: str,
        display_header: bool,
    ):
        """Shortcut for /post with mandatory mentions and no header."""
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

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option("user", description="The user who wrote the post")
    @option("content", description="What to search for", required=False)
    @option("character", description="The character name. Invalid names ignored.", required=False)
    @option("mentioning", description="A user mentioned in the post", required=False)
    @option("after", description="Only show posts after a date (YYYY-MM-DD)", required=False)
    @option("before", description="Only show posts before a date (YYYY-MM-DD)", required=False)
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
    @option(
        "sort_order",
        description="The sort order (default 'Most relevant' or 'Newest' if no search term)",
        choices=[
            OptionChoice("Most relevant", 0),
            OptionChoice("Least relevant", 1),
            OptionChoice("Newest", 2),
            OptionChoice("Oldest", 3),
        ],
        default=0,
    )
    async def search(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        content: str,
        character: str,
        mentioning: discord.Member,
        after: str,
        before: str,
        hidden: bool,
        summary: bool,
        sort_order: int,
    ):
        """Search for a Rolepost. Displays up to 5 results."""
        await inconnu.roleplay.search(
            ctx,
            user,
            content,
            character,
            mentioning,
            after,
            before,
            hidden,
            summary,
            sort_order,
        )

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def tags(self, ctx: discord.ApplicationContext):
        """View your Rolepost tags."""
        await inconnu.roleplay.show_tags(ctx)

    # Message commands

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def bookmarks(self, ctx: discord.ApplicationContext):
        """View your Rolepost bookmarks."""
        await inconnu.roleplay.show_bookmarks(ctx)

    @commands.message_command(name="Post: Edit", contexts={discord.InteractionContextType.guild})
    async def edit_rp_post(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Edit the selected Rolepost."""
        await inconnu.roleplay.edit_post(ctx, message)

    @commands.message_command(name="Post: Delete", contexts={discord.InteractionContextType.guild})
    async def delete_rp_post(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Delete the selected Rolepost."""
        await inconnu.roleplay.delete_message_chain(ctx, message)

    # Listeners

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk mark Roleposts as deleted."""
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
            logger.debug("POST: Marking {} potential Roleposts as deleted", len(updates))
            await db.rp_posts.bulk_write(updates)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Mark a Rolepost as deleted and post a notice in the guild's deletion
        channel."""
        if (message := raw_message.cached_message) is not None:
            if message.webhook_id is None:
                return
            if not message.author.bot:
                return
            if message.author == self.bot.user:
                return
            if message.flags.ephemeral:
                # This shouldn't ever be true given ephemerals are only from
                # the bot user. In case this ever changes in the future,
                # though, we're ready!
                return

        # We can't rely on ensuring there's a webhook, so we fetch if it's a
        # bot message or a message not in the cache. Hopefully it isn't too
        # expensive ...
        post = await db.rp_posts.find_one_and_update(
            {"message_id": raw_message.message_id},
            {"$set": {"deleted": True, "deletion_date": discord.utils.utcnow()}},
        )
        if post is not None:
            logger.debug("POST: Marked Rolepost as deleted")
            deletion_id = await services.settings.deletion_channel(post["guild"])
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
                    logger.info(
                        "POST: Sent deletion notice to deletion at {}: {}",
                        post["guild"],
                        deletion_id,
                    )
                except discord.Forbidden:
                    logger.info(
                        "POST: Unable to send deletion notice to {}: {} (Missing permissions)",
                        post["guild"],
                        deletion_id,
                    )
                except discord.HTTPException:
                    logger.info(
                        "POST: Unable to send deletion notice to {}: {} (Channel not found)",
                        post["guild"],
                        deletion_id,
                    )
            else:
                logger.debug("POST: No deletion channel set on {}", post["guild"])
        else:
            logger.debug("POST: Deleted message is not a Rolepost")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Mark Roleposts in the deleted channel."""
        logger.info("POST: Marking all Roleposts in {} as deleted", channel.name)
        await db.rp_posts.update_many(
            {"channel": channel.id},
            {"$set": {"deleted": True, "deletion_date": discord.utils.utcnow()}},
        )


def setup(bot):
    """Set up the cog."""
    bot.add_cog(RoleplayCog(bot))
