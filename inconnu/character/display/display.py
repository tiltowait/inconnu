"""character/display/display.py - Tools for displaying characters."""
# pylint: disable=too-many-arguments

import discord

from . import trackmoji
from ... import common
from ...vchar import errors, VChar
from ...settings import Settings as settings

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-display"

# Display fields

HEALTH = 0
WILLPOWER = 1
HUMANITY = 2
POTENCY = 3
HUNGER = 4
EXPERIENCE = 5


async def display_requested(ctx, character=None, message=None, player=None):
    """Display a character as directly requested by a user."""
    try:
        owner = await common.player_lookup(ctx, player)

        character = VChar.fetch(ctx.guild.id, owner.id, character)
        await display(ctx, character,
            owner=player,
            message=message,
            footer=f"To view traits: /traits list character:{character.name}"
        )
        #await __display_character(ctx, character, owner, message)

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
        embed.set_author(name=owner.display_name, icon_url=owner.display_avatar)
        embed.set_footer(text="To view one: /character display character:NAME")
        await ctx.respond(embed=embed, hidden=False)

    except errors.CharacterError as err:
        await common.present_error(ctx, err, author=owner, help_url=__HELP_URL)
    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)


async def display(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None
):
    """
    Display a character.
    Args:
        ctx: The Discord context with which to display
        character (VChar): The character to display
        title (str): The embed's title
        message (str): The message to display alongside the fields
        footer (str): The embed's footer
        owner (discord.Member): The player who owns the character
        fields ([tuple]): The fields to display, as well as their titles
        custom ([tuple]): Custom fields to display, as well as their titles
    """
    if settings.accessible(ctx.author):
        await __display_text(ctx, character,
            title=title,
            message=message,
            footer=footer,
            owner=owner,
            fields=fields,
            custom=custom
        )
    else:
        await __display_embed(ctx, character,
            title=title,
            message=message,
            footer=footer,
            owner=owner,
            fields=fields,
            custom=custom
        )


async def __display_embed(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None
):
    if owner is None:
        owner = ctx.author

    if fields is None:
        fields = [
            ("Health", HEALTH),
            ("Willpower", WILLPOWER),
            ("Humanity", HUMANITY),
            ("Blood Potency", POTENCY),
            ("Hunger", HUNGER),
            ("Experience", EXPERIENCE)
        ]

    # Begin building the embed
    embed = discord.Embed(
        title=title or character.name,
        description=message or ""
    )

    author_name = owner.display_name if title is None else character.name
    embed.set_author(name=author_name, icon_url=owner.display_avatar)
    embed.set_footer(text=footer or "")

    for field, parameter in fields:
        if parameter == HEALTH:
            value = trackmoji.emojify_track(character.health)
        elif parameter == WILLPOWER:
            value = trackmoji.emojify_track(character.willpower)
        elif parameter == HUMANITY:
            value = trackmoji.emojify_humanity(character.humanity, character.stains)
        elif parameter == POTENCY:
            if character.splat != "vampire":
                continue
            value = trackmoji.emojify_blood_potency(character.potency)
        elif parameter == HUNGER:
            if character.splat != "vampire":
                continue
            value = trackmoji.emojify_hunger(character.hunger)
        elif parameter == EXPERIENCE:
            value = "```\n"
            value += f"{character.current_xp} / {character.total_xp}\n"
            value += "```"

        embed.add_field(name=field, value=value, inline=False)

    if custom is not None:
        for field, value in custom:
            embed.add_field(name=field, value=value, inline=False)

    await ctx.respond(embed=embed)


async def __display_text(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None
):
    """Display a text representation of the character."""
    if owner is None:
        owner = ctx.author

    if fields is None:
        fields = [
            ("Health", HEALTH),
            ("Willpower", WILLPOWER),
            ("Humanity", HUMANITY),
            ("Blood Potency", POTENCY),
            ("Hunger", HUNGER),
            ("Experience", EXPERIENCE)
        ]

    # Begin drafting the contents
    contents = []
    contents.append("**" + (title or character.name) + "**")

    if message is not None:
        contents.append(message)

    contents.append("") # Blank line

    for field, parameter in fields:
        if parameter == HEALTH:
            contents.append(f"**{field}:** {character.health}")
        elif parameter == WILLPOWER:
            contents.append(f"**{field}:** {character.willpower}")
        elif parameter == HUMANITY:
            contents.append(f"**{field}:** {character.humanity}, **Stains:** {character.stains}")
        elif parameter == POTENCY:
            if character.splat != "vampire":
                continue
            contents.append(f"**{field}:** {character.potency}")
        elif parameter == HUNGER:
            if character.splat != "vampire":
                continue
            contents.append(f"**{field}:** {character.hunger}")
        elif parameter == EXPERIENCE:
            contents.append(f"**{field}:** {character.current_xp} / {character.total_xp}")

    if custom is not None:
        contents.append("")
        for field, value in custom:
            contents.append(f"**{field}:** {value}")

    contents = "\n".join(contents)
    if footer is not None:
        contents += "\n\n" + footer
    await ctx.respond(contents)
