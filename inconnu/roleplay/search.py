"""Post search functionality."""

import discord
from bson.objectid import ObjectId
from discord.ext.pages import Paginator

import inconnu
from inconnu.models import RPPost


async def search(
    ctx,
    user: discord.Member,
    needle: str,
    mentioning: discord.Member,
    ephemeral: bool,
    charid: ObjectId = None,
):
    """Search RP posts for a given string."""
    needle = " ".join(needle.split())  # Normalize
    search_meta = None

    query = {"deleted": False, "guild": ctx.guild_id, "user": user.id}
    if needle:
        query["$text"] = {"$search": needle}
        search_meta = {"$meta": "textScore"}
    if mentioning is not None:
        query["mentions"] = mentioning.id
    if charid is not None:
        query["charid"] = charid

    posts = []
    num = 1
    async for post in RPPost.find(query).sort("content", search_meta).limit(20):
        # Make an embed for each post
        embed = inconnu.roleplay.post_embed(
            post,
            author=user.display_name,
            icon_url=user.display_avatar,
            footer=f"Search key: {needle}",
        )

        posts.append(embed)
        num += 1

    if posts:
        paginator = Paginator(posts)
        await paginator.respond(ctx.interaction, ephemeral=ephemeral)
    else:
        # Construct the error message
        err = f"No posts by {user.mention} found"
        conditions = []
        if needle:
            conditions.append(f"matching `{needle}`")
        if mentioning is not None:
            conditions.append(f"mentioning {mentioning.mention}")

        if conditions:
            err += " " + " and ".join(conditions)
        err += "."

        await inconnu.utils.error(ctx, err, title="Not found")
