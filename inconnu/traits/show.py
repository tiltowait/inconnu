"""traits/show.py - Display character traits."""

import discord
from discord.ext import pages

import inconnu

__HELP_URL = "https://www.inconnu.app/#/trait-management?id=displaying-traits"


async def show(ctx, character: str, player: discord.Member):
    """Present a character's traits to its owner."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        owner=player,
        tip="`/traits list` `character:CHARACTER`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    embed = traits_embed(character, haven.owner)
    await inconnu.respond(ctx)(embed=embed, ephemeral=True)


def traits_embed(character, owner):
    """Display traits in an embed."""
    embed = discord.Embed(title="Character Traits")
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(owner))
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
        # Sort them first
        user_defined = sorted(char_traits.items(), key=lambda s: s[0].casefold())

        traits = [f"***{trait}:*** {rating}" for trait, rating in user_defined]
        traits = "\n".join(traits)
        embed.add_field(name="​", value=f"**USER-DEFINED**\n{traits}", inline=False)

    return embed
