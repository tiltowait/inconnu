"""Post search functionality."""

import discord
from bson.objectid import ObjectId
from discord.ext.pages import Paginator

import inconnu
from inconnu.models import RPPost


async def search(ctx, user: discord.Member, needle: str, ephemeral: bool, charid: ObjectId = None):
    """Search RP posts for a given string."""
    needle = " ".join(needle.split())
    # TODO: More needle processing

    query = {"deleted": False, "guild": ctx.guild_id, "user": user.id, "$text": {"$search": needle}}
    if charid is not None:
        query["charid"] = charid

    posts = []
    num = 1
    async for post in RPPost.find(query).sort("content", {"$meta": "textScore"}).limit(5):
        # Make an embed for each post
        embed = discord.Embed(
            title=f"Post #{num}: {post.header.char_name}",
            description=post.content,
            url=post.url,
            timestamp=post.utc_date,
        )
        embed.set_footer(text=f"Search key: {needle}")
        embed.set_author(name=user.display_name, icon_url=user.display_avatar)

        posts.append(embed)
        num += 1

    if posts:
        paginator = Paginator(posts)
        await paginator.respond(ctx.interaction, ephemeral=ephemeral)
    else:
        await inconnu.utils.error(
            ctx,
            f"No posts by {user.mention} found matching `{needle}`.",
            title="Not found",
        )
