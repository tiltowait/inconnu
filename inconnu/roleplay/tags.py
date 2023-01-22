"""Tag display and selection."""

import discord
from discord.ext.pages import Page, Paginator

import inconnu


async def show_tags(ctx: discord.ApplicationContext):
    """Show the user's tags with an option to select and view messages."""
    pipeline = [
        {
            "$match": {
                "deleted": False,
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "tags": {"$exists": True, "$ne": []},
            }
        },
        {"$project": {"_id": 1, "tags": 1}},  # Speed up large result sets
        {"$unwind": "$tags"},
        # We want to sort by count, then name, so we can't use $sortByCount
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]

    pages = []
    current_tags = []
    async for tag in inconnu.db.rp_posts.aggregate(pipeline):
        # A Discord select menu can only hold a maximum of 25 items, so we will
        # make our pages hold no more than 25 tags each
        current_tags.append((tag["_id"], tag["count"]))

        if len(current_tags) == 25:
            pages.append(_create_page(ctx, current_tags))
            current_tags = []

    if current_tags:
        # We have some leftovers
        pages.append(_create_page(ctx, current_tags))

    if pages:
        # Only show buttons if there is more than one page. The indicator
        # must be explicitly disabled.
        show_buttons = len(pages) > 1
        paginator = Paginator(pages, show_disabled=show_buttons, show_indicator=show_buttons)
        await paginator.respond(ctx.interaction, ephemeral=True)
    else:
        post = ctx.bot.cmd_mention("post")
        await inconnu.utils.error(
            ctx,
            f"Set tags in {post} or add to old posts via right-click.",
            title="You have no tags!",
        )


def _create_page(ctx: discord.ApplicationContext, tags: list[tuple[str, int]]) -> Page:
    """Creates a tag page."""
    embed = discord.Embed(
        title="RP Post Tags",
        description="\n".join(map(lambda t: f"{t[1]}: `{t[0]}`", tags)),
    )
    embed.set_author(
        name=ctx.user.display_name,
        icon_url=inconnu.get_avatar(ctx.user),
    )

    post = ctx.bot.cmd_mention("post")
    embed.add_field(
        name="\u200b",
        value=f"Set tags in {post} or add to old posts via right-click.",
    )

    return Page(embeds=[embed], custom_view=TagView(tags))


class TagView(inconnu.views.DisablingView):
    """A View for selecting and displaying tags."""

    def __init__(self, tags: list[tuple[str, int]], *args, **kwargs):
        super().__init__(timeout=600, *args, **kwargs)

        select = discord.ui.Select(
            placeholder="Select a tag to view posts",
            options=[discord.SelectOption(label=tag[0]) for tag in tags],
        )
        select.callback = self.callback

        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        """Present the posts with the tag."""
        selected = self.children[0].values[0]

        query = {
            "deleted": False,
            "guild": interaction.guild_id,
            "user": interaction.user.id,
            "tags": selected,
        }
        pages = []
        async for post in inconnu.models.RPPost.find(query):
            pages.append(inconnu.roleplay.post_embed(post, footer=f"Tag: {selected}"))

        if pages:
            show_buttons = len(pages) > 1
            paginator = Paginator(
                pages=pages, show_disabled=show_buttons, show_indicator=show_buttons
            )
            await paginator.respond(interaction, ephemeral=True)
        else:
            await inconnu.utils.error(
                interaction, f"No posts with tag {selected} found.", title="No posts found!"
            )
