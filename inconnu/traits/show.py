"""traits/show.py - Display character traits."""

import discord

import inconnu
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/traits/displaying-traits"


@haven(__HELP_URL)
async def show(ctx, character: str, *, player: discord.Member):
    """Present a character's traits to its owner."""
    embed = traits_embed(ctx, character, player)
    await ctx.respond(embed=embed, ephemeral=True)


def traits_embed(
    ctx: discord.ApplicationContext | discord.Interaction,
    character: "VChar",
    owner: discord.Member = None,
):
    """Display traits in an embed."""
    embed = inconnu.utils.VCharEmbed(ctx, character, owner, title="Character Traits")
    embed.set_footer(text="To see HP, WP, etc., use /character display")

    char_traits = character.traits  # This is an automatic copy

    for group, subgroups in inconnu.constants.GROUPED_TRAITS.items():
        embed.add_field(name="​", value=f"**{group}**", inline=False)
        for subgroup, traits in subgroups.items():
            trait_list = []
            for trait in traits:
                for index, char_trait in enumerate(char_traits):
                    if char_trait.matching(trait, True):
                        trait_list.append(f"**{char_trait.name}:** {char_trait.rating}")
                        del char_traits[index]

            embed.add_field(name=subgroup, value="\n".join(trait_list), inline=True)

    # The remaining traits are user-defined
    if char_traits:
        # Sort them first
        user_defined = sorted(char_traits, key=lambda s: s.name.casefold())

        traits = [f"***{trait.name}:*** {trait.rating}" for trait in user_defined]
        traits = "\n".join(traits)
        embed.add_field(name="​", value=f"**USER-DEFINED**\n{traits}", inline=False)

    return embed
