"""RP post bookmarks."""

from datetime import timezone

import discord
from discord.ext.commands import Paginator as Chunker
from discord.ext.pages import Paginator

import inconnu


async def show_bookmarks(ctx: discord.ApplicationContext):
    """Show the users's bookmarks."""
    chunker = Chunker(prefix="", suffix="")
    pipeline = [
        {
            "$match": {
                "deleted": False,
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "title": {"$ne": None},
            }
        },
        {"$project": {"_id": 1, "title": 1, "date": 1, "url": 1}},
        {"$sort": {"date": -1}},
    ]
    async for bookmark in inconnu.db.rp_posts.aggregate(pipeline):
        title = bookmark["title"]
        url = bookmark["url"]
        date = inconnu.gen_timestamp(bookmark["date"].replace(tzinfo=timezone.utc), "d")
        chunker.add_line(f"{date}: **[{title}]({url})**")

    post = ctx.bot.cmd_mention("post")
    tip = f"Set bookmarks in {post}. You may add bookmarks to old posts via right-click."

    pages = []
    for chunk in chunker.pages:
        embed = discord.Embed(title="RP Bookmarks", description=chunk)
        embed.set_author(
            name=ctx.user.display_name,
            icon_url=inconnu.get_avatar(ctx.user),
        )
        embed.add_field(name="\u200b", value=tip)

        pages.append(embed)

    if pages:
        show_buttons = len(pages) > 1
        paginator = Paginator(
            pages,
            show_disabled=show_buttons,
            show_indicator=show_buttons,
            loop_pages=show_buttons,
        )
        await paginator.respond(ctx.interaction, ephemeral=True)
    else:
        await inconnu.utils.error(ctx, tip, title="You have no bookmarks!")
