"""Post search functionality."""

import re

import discord
from bson import ObjectId
from discord.ext.pages import Paginator
from pymongo import DESCENDING

import inconnu
from inconnu.models import RPPost


async def search(
    ctx,
    user: discord.Member,
    needle: str,
    mentioning: discord.Member,
    ephemeral: bool,
    summary: bool,
    charid: ObjectId = None,
):
    """Search RP posts for a given string."""
    needle = " ".join(needle.split())  # Normalize

    query = {"deleted": False, "guild": ctx.guild_id, "user": user.id}
    footer = []

    if needle:
        query["$text"] = {"$search": needle}
        footer.append(f"Search key: {needle}")
        sort_key = ("content", {"$meta": "textScore"})
    else:
        # They're just getting recent posts
        sort_key = ("date", DESCENDING)
    if mentioning is not None:
        query["mentions"] = mentioning.id
        footer.append(f"Mentioning {user.display_name}")
    if charid is not None:
        query["charid"] = charid

    posts = []  # Will either contain strings or embeds
    async for post in RPPost.find(query).sort(*sort_key).limit(25):
        if summary:
            # Show only links to posts
            timestamp = discord.utils.format_dt(post.utc_date, "d")
            sanitized = re.sub(r"[^\w\s]", "", post.content).replace("\n", " ")
            preview = sanitized[:20].strip() + " ..."

            posts.append(f"{timestamp}: [{preview}]({post.url})")
        else:
            # Make an embed for each post
            embed = inconnu.roleplay.post_embed(
                post,
                author=user.display_name,
                icon_url=inconnu.get_avatar(user),
                footer=" • ".join(footer),
            )
            embed.add_field(name=" ", value=post.url)
            posts.append(embed)

    if posts:
        if summary:
            # Still need to construct the embed
            embed = discord.Embed(title="Recent Posts", description="\n".join(posts))
            embed.set_author(name=user.display_name, icon_url=inconnu.get_avatar(user))
            if footer:
                embed.set_footer(text=" • ".join(footer))

            await ctx.respond(embed=embed, ephemeral=ephemeral)
        else:
            paginator = Paginator(posts, loop_pages=len(posts) > 1)
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
