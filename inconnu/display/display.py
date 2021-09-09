"""display.py - Tools for displaying characters."""

import discord

from . import trackmoji
from ..constants import character_db
from ..databases import CharacterNotFoundError

async def parse(ctx, character=None):
    """Determine which character to display, then display them."""
    try:
        char_name = None
        char_id = None

        if character is None:
            user_chars = await character_db.characters(ctx.guild.id, ctx.author.id)

            if len(user_chars) == 0:
                raise ValueError("You have no characters.")

            if len(user_chars) > 1:
                # Give them a list of characters
                user_chars = list(user_chars.keys())
                user_chars = "\n".join(user_chars)

                response = f"**You have the following characters:**\n{user_chars}"
                response += "\n\nView one with `/display NAME`"

                raise ValueError(response)

            if len(user_chars) == 1:
                # Display their only character
                char_name, char_id = list(user_chars.items())[0]

        else:
            char_name, char_id = await character_db.character(ctx.guild.id, ctx.author.id, character)

        # Character has been found
        await __display_character(ctx, char_name, char_id)

    except (ValueError, CharacterNotFoundError) as err:
        await ctx.respond(str(err), hidden=True)


async def __display_character(ctx, char_name: str, char_id: int):
    """Display the basic traits for the character."""

    # The user might have not provided proper capitalization, so get the name again
    splat = await character_db.get_splat(char_id)
    humanity = await character_db.get_humanity(char_id)
    stains = await character_db.get_stains(char_id)
    health = await character_db.get_health(char_id)
    willpower = await character_db.get_willpower(char_id)
    current_xp = await character_db.get_current_xp(char_id)
    total_xp = await character_db.get_total_xp(char_id)

    health = trackmoji.emojify_track(health)
    willpower = trackmoji.emojify_track(willpower)
    humanity = trackmoji.emojify_humanity(humanity, stains)

    embed = discord.Embed(
        title=char_name,
        footer=f"To view traits: //display traits {char_name}"
    )
    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.avatar_url
    )
    embed.add_field(name="Health", value=health, inline=False)
    embed.add_field(name="Willpower", value=willpower, inline=False)
    embed.add_field(name="Humanity", value=humanity, inline=False)

    if splat == 0:
        hunger = await character_db.get_hunger(char_id)
        potency = await character_db.get_potency(char_id)
        hunger = trackmoji.emojify_hunger(hunger)
        potency = trackmoji.emojify_blood_potency(potency)

        embed.add_field(name="Blood Potency", value=potency, inline=False)
        embed.add_field(name="Hunger", value=hunger, inline=False)

    if total_xp > 0:
        embed.add_field(name="Experience", value=__format_xp(current_xp, total_xp))

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
