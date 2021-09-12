"""character/display/display.py - Tools for displaying characters."""

import discord

from . import trackmoji
from ... import common
from ...vchar import errors, VChar

async def parse(ctx, character=None, message=None):
    """Determine which character to display, then display them."""
    try:
        if character is None:
            user_chars = VChar.all_characters(ctx.guild.id, ctx.author.id)

            if len(user_chars) == 0:
                raise ValueError("You have no characters.")

            if len(user_chars) > 1:
                user_chars = "\n".join(map(lambda char: char.name, user_chars))
                raise errors.CharacterError(user_chars)

            if len(user_chars) == 1:
                # Display their only character
                character = user_chars[0]

        else:
            character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)

        # Character has been found
        await __display_character(ctx, character, message)

    except ValueError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
    except errors.CharacterError as err:
        embed = discord.Embed(
            title="Your Characters",
            description=str(err)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="To view one: /character display NAME")

        await ctx.respond(embed=embed, hidden=True)


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
