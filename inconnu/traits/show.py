"""traits/show.py - Display character traits."""

import discord
from discord.ext import pages

import inconnu
from .. import common

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=displaying-traits"


async def show(ctx, character: str, player: discord.Member):
    """Present a character's traits to its owner."""
    try:
        owner = await common.player_lookup(ctx, player)
        tip = "`/traits list` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        if await inconnu.settings.accessible(ctx.user):
            await __list_text(ctx, character)
        else:
            await __list_embed(ctx, character, owner)

    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except common.FetchError:
        pass


async def __list_embed(ctx, character, owner):
    """Display traits in an embed."""
    embed = discord.Embed(title="Character Traits")
    embed.set_author(name=character.name, icon_url=owner.display_avatar)
    embed.set_footer(text="To see HP, WP, etc., use /character display")

    char_traits = character.traits

    for group, subgroups in inconnu.constants.GROUPED_TRAITS.items():
        embed.add_field(name="​", value=f"**{group}**", inline=False)
        for subgroup, traits in subgroups.items():
            trait_list = []
            for trait in traits:
                rating = char_traits.pop(trait, 0)
                trait_list.append(f"***{trait}:*** {rating}")

            embed.add_field(name=subgroup, value="\n".join(trait_list), inline=True)

    # The remaining traits are user-defined
    if char_traits:
        traits = [f"***{trait}:*** {rating}" for trait, rating in char_traits.items()]
        traits = "\n".join(traits)
        embed.add_field(name="​", value=f"**USER-DEFINED**\n{traits}", inline=False)

    await inconnu.respond(ctx)(embed=embed, ephemeral=True)


async def __list_text(ctx, character):
    """Display traits in plain text."""
    traits = [f"{trait}: {rating}" for trait, rating in character.traits.items()]
    raw_pages = common.paginate(1200, *traits) # Array of strings

    _pages = []
    for page in raw_pages:
        contents = [f"{character.name}'s Traits"]
        contents.append("```css")
        contents.append(page)
        contents.append("```")
        contents.append("To see HP, WP, etc., use `/character display`")

        _pages.append("\n".join(contents))

    paginator = pages.Paginator(pages=_pages, show_disabled=False)
    await paginator.respond(ctx.interaction, ephemeral=True)
