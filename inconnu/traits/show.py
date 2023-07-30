"""traits/show.py - Display character traits."""

import discord
from discord.ext.commands import Paginator as Chunker
from discord.ext.pages import Paginator

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
    specialties = []
    for group, subgroups in inconnu.constants.GROUPED_TRAITS.items():
        embed.add_field(name="​", value=f"**{group}**", inline=False)
        for subgroup, traits in subgroups.items():
            trait_list = []
            for trait in traits:
                found = False
                for index, char_trait in enumerate(char_traits):
                    if char_trait.matching(trait, True):
                        if char_trait.has_specialties:
                            specs = inconnu.utils.format_join(char_trait.specialties, ", ", "`")
                            spec = f"**{char_trait.name}:** {specs}"
                            specialties.append(spec)

                        trait_list.append(f"**{trait}:** {char_trait.rating}")
                        del char_traits[index]
                        found = True
                        break
                if not found:
                    trait_list.append(f"**{trait}:** 0")

            embed.add_field(name=subgroup, value="\n".join(trait_list), inline=True)

    # The remaining traits are user-defined
    custom = []
    disciplines = []

    for trait in char_traits:
        entry = f"**{trait.name}:** {trait.rating}"
        if trait.is_discipline:
            if trait.has_specialties:
                # If it has any powers, show them
                powers = inconnu.utils.format_join(trait.specialties, ", ", "`")
                entry += f" ({powers})"
            disciplines.append(entry)
        else:
            custom.append(entry)

    # Fill in the custom stuff
    nbsp = "*None*"
    embed.add_field(name="​", value="**USER-DEFINED**", inline=False)
    embed.add_field(name="Disciplines", value="\n".join(disciplines) or nbsp, inline=False)

    # If a character has many specialties, this can become too long. This fix
    # is a kludge and needs to be replaced by something more robust.
    chunker = Chunker(prefix="", suffix="", max_size=1024)
    for spec in specialties:
        chunker.add_line(spec)

    if chunker.pages:
        embed.add_field(name="Specialties", value=chunker.pages[0], inline=False)
        for page in chunker.pages[1:]:
            embed.add_field(name=" ", value=page, inline=False)

    embed.add_field(name="Custom", value="\n".join(custom) or nbsp, inline=False)

    return embed
