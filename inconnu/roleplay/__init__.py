"""Package interface for RP commands."""

import discord

import inconnu.models
from inconnu.roleplay.bookmarks import show_bookmarks
from inconnu.roleplay.delete import delete_message_chain
from inconnu.roleplay.post import create_post as post
from inconnu.roleplay.post import edit_post
from inconnu.roleplay.search import search
from inconnu.roleplay.tags import show_tags

__all__ = (
    "delete_message_chain",
    "edit_post",
    "post",
    "post_embed",
    "search",
    "show_bookmarks",
    "show_tags",
)


def post_embed(
    post_doc: inconnu.models.RPPost,
    author: str = None,
    footer: str = None,
    icon_url=None,
) -> discord.Embed:
    """Generate a Rolepost embed."""
    embed = discord.Embed(
        title=post_doc.header.char_name,
        description=post_doc.content,
        url=post_doc.url,
        timestamp=post_doc.utc_date,
    )

    if author:
        embed.set_author(name=author, icon_url=icon_url)
    if footer:
        embed.set_footer(text=footer)

    return embed
