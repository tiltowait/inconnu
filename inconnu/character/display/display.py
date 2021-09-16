"""character/display/display.py - Tools for displaying characters."""

import discord

from . import trackmoji
from ... import common
from ...vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-display"


async def parse(ctx, character=None, message=None, player=None):
    """Determine which character to display, then display them."""
    try:
        owner = await common.player_lookup(ctx, player)

        character = VChar.fetch(ctx.guild.id, owner.id, character)
        await __display_character(ctx, character, owner, message)

    except errors.UnspecifiedCharacterError as err:
        characters = [char.name for char in VChar.all_characters(ctx.guild.id, owner.id)]

        if ctx.author == owner:
            title = "Your Characters"
        else:
            title = f"{owner.display_name}'s Characters"

        embed = discord.Embed(
            title=title,
            description="\n".join(characters)
        )
        embed.set_author(name=owner.display_name, icon_url=owner.avatar_url)
        embed.set_footer(text="To view one: /character display character:NAME")
        await ctx.respond(embed=embed, hidden=False)

    except errors.CharacterError as err:
        await common.present_error(ctx, err, author=owner, help_url=__HELP_URL)
    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)


async def __display_character(ctx, character: VChar, owner, message):
    """Display the character's basic traits."""
    embed = discord.Embed(
        title=character.name,
        footer=f"To view traits: /traits list {character.name}"
    )

    if message is not None:
        embed.description = message

    embed.set_author(
        name=owner.display_name,
        icon_url=owner.avatar_url
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
