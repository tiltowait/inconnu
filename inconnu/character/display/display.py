"""character/display/display.py - Tools for displaying characters."""

import discord

from . import trackmoji
from ... import common
from ...vchar import errors, VChar

async def parse(ctx, character=None, message=None):
    """Determine which character to display, then display them."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
        await __display_character(ctx, character, message)

    except errors.UnspecifiedCharacterError as err:
        characters = [char.name for char in VChar.all_characters(ctx.guild.id, ctx.author.id)]
        embed = discord.Embed(
            title="Your Characters",
            description="\n".join(characters)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="To view one: /character display character:NAME")
        await ctx.respond(embed=embed, hidden=False)

    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)


async def __display_character(ctx, character: VChar, message=None):
    """Display the character's basic traits."""
    embed = discord.Embed(
        title=character.name,
        footer=f"To view traits: /traits list {character.name}"
    )

    if message is not None:
        embed.description = message

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.avatar_url
    )

    # Set the universal tracks
    health = trackmoji.emojify_track(character.health)
    willpower = trackmoji.emojify_track(character.willpower)
    humanity = trackmoji.emojify_humanity(character.humanity, character.stains)

    embed.add_field(name="Health", value=health, inline=False)
    embed.add_field(name="Willpower", value=willpower, inline=False)
    embed.add_field(name="Humanity", value=humanity, inline=False)

    if character.splat == "vampire":
        hunger = trackmoji.emojify_hunger(character.hunger)
        potency = trackmoji.emojify_blood_potency(character.potency)

        embed.add_field(name="Blood Potency", value=potency, inline=False)
        embed.add_field(name="Hunger", value=hunger, inline=False)

    embed.add_field(
        name="Experience",
        value=__format_xp(character.current_xp, character.total_xp)
    )

    # There are still commands that need reply()
    if hasattr(ctx, "respond"):
        await ctx.respond(embed=embed)
    else:
        await ctx.reply(embed=embed)


def __format_xp(current: int, total: int) -> str:
    """Format the character's XP."""
    experience = "```\n"
    experience += f"{current} / {total}\n"
    experience += "```"

    return experience
