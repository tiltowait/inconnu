"""Post search functionality."""

import re
from datetime import datetime, timezone
from enum import Enum

import discord
from discord.ext.pages import Paginator
from loguru import logger
from pymongo import ASCENDING, DESCENDING

import inconnu
from inconnu.models import RPPost


class SortOrder(Enum):
    """The search results sort order."""

    MOST_RELEVANT = 0
    LEAST_RELEVANT = 1
    NEWEST = 2
    OLDEST = 3


async def search(
    ctx,
    user: discord.Member,
    needle: str | None,
    character: str | None,
    mentioning: discord.Member,
    after: str,
    before: str,
    ephemeral: bool,
    summary: bool,
    sort_order: int,
):
    """Search Roleposts for a given string."""
    query = {"deleted": False, "guild": ctx.guild_id, "user": user.id}
    footer = []
    reverse_results = False

    match SortOrder(sort_order):
        case SortOrder.MOST_RELEVANT:
            if needle:
                sort_key = ("content", {"$meta": "textScore"})
            else:
                # No needle means no text search
                sort_key = ("date", DESCENDING)
        case SortOrder.LEAST_RELEVANT:
            if needle:
                sort_key = ("content", {"$meta": "textScore"})
                # MongoDB doesn't let us reverse this sort, so we have to do
                # it manually
                reverse_results = True
            else:
                sort_key = ("date", DESCENDING)
        case SortOrder.NEWEST:
            sort_key = ("date", DESCENDING)
        case SortOrder.OLDEST:
            sort_key = ("date", ASCENDING)

    if needle:
        needle = " ".join(needle.split())  # Normalize
        query["$text"] = {"$search": needle}
        footer.append(f"Search key: {needle}")

    if character:
        if inconnu.character.valid_name(character):
            query["header.char_name"] = re.compile(character, re.I)
        else:
            logger.debug("RP SEARCH: Ignoring invalid character name")
    if mentioning is not None:
        query["mentions"] = mentioning.id
        footer.append(f"Mentioning {user.display_name}")

    try:
        after, before = convert_dates(after, before)
        dt_query = {}
        if after:
            dt_query["$gt"] = after
        if before:
            dt_query["$lt"] = before
        if dt_query:
            query["date"] = dt_query
    except (ValueError, SyntaxError) as err:
        await inconnu.embeds.error(ctx, err, title="Invalid date")
        return

    posts = []  # Will either contain strings or embeds
    async for post in RPPost.find(query).sort(sort_key).limit(25):
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
            embed.add_field(name=" ", value=str(post.url))
            posts.append(embed)

    if posts:
        if reverse_results:
            posts = posts[::-1]

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
        err = f"No posts by {user.mention} found with the given search parameters:"
        conditions = []
        if needle:
            conditions.append(f"* Matching `{needle}`")
        if mentioning is not None:
            conditions.append(f"* Mentioning {mentioning.mention}")
        if after:
            conditions.append(f"* After `{after}`")
        if before:
            conditions.append(f"* Before `{before}`")

        if conditions:
            err += "\n" + "\n".join(conditions)
        err += "."

        await inconnu.embeds.error(ctx, err, title="Not found")


def convert_dates(after: str, before: str) -> tuple[datetime, datetime]:
    """Convert the before and after strings to proper datetimes.
    Removes timezone info.

    Raises:
        ValueError if before is after after.
        ParserError if a datetime can't be inferred."""

    def convert_tzs(dt: str | None) -> datetime | None:
        """If the datetime has a timezone, convert it to UTC and remove it."""
        if dt is None:
            return None
        try:
            dt = datetime.strptime(dt, "%Y%m%d")
            if dt.tzinfo is None:
                return dt
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError as err:
            raise SyntaxError(f"Invalid date: `{dt}`.\nAccepted format: YYYYMMDD.") from err

    after = convert_tzs(after)
    before = convert_tzs(before)

    if before and after:
        if before <= after:
            raise ValueError("`before` must occur after `after`.")

    return after, before
