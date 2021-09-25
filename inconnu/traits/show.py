"""traits/show.py - Display character traits."""

import asyncio

import discord

from .. import common
from ..settings import Settings

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=displaying-traits"


async def show(ctx, character: str, player: discord.Member):
    """Present a character's traits to its owner."""
    try:
        owner = await common.player_lookup(ctx, player)
        tip = "`/traits list` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        if Settings.accessible(ctx.author):
            await __list_text(ctx, character)
        else:
            await __list_embed(ctx, character, owner)

    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except common.FetchError:
        pass


async def __list_embed(ctx, character, owner):
    """Display traits in an embed."""
    traits = [f"**{trait}:** {rating}" for trait, rating in character.traits.items()]
    pages = common.paginate(1200, *traits) # Array of strings

    for page_num, page in enumerate(pages):
        embed = discord.Embed(
            title="Traits" if len(pages) == 1 else f"Traits: Page {page_num + 1} of {len(pages)}",
            description=page
        )
        embed.set_author(name=character.name, icon_url=owner.display_avatar)
        embed.set_footer(text="To see HP, WP, etc., use /character display")

        await ctx.respond(embed=embed, hidden=True)
        await asyncio.sleep(0.5)


async def __list_text(ctx, character):
    """Display traits in plain text."""
    traits = [f"{trait}: {rating}" for trait, rating in character.traits.items()]
    pages = common.paginate(1200, *traits) # Array of strings

    for page_num, page in enumerate(pages):
        if len(pages) == 1:
            contents = [f"{character.name}'s Traits"]
        else:
            contents = [f"{character.name}'s Traits: Page {page_num + 1} of {len(pages)}"]
        contents.append("```css")
        contents.append(page)
        contents.append("```")
        contents.append("To see HP, WP, etc., use `/character display`")

        await ctx.respond("\n".join(contents), hidden=True)
        await asyncio.sleep(0.5)
