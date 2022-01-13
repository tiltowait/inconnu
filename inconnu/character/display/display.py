"""character/display/display.py - Tools for displaying characters."""
# pylint: disable=too-many-arguments

import asyncio

import discord
from discord_ui import Button

from . import trackmoji
from ... import common
from ... import traits
from ...constants import DAMAGE
from ...settings import Settings
from ...vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-display"

# Display fields

HEALTH = 0
WILLPOWER = 1
HUMANITY = 2
POTENCY = 3
HUNGER = 4
EXPERIENCE = 5
SEVERITY = 6


async def display_requested(ctx, character=None, message=None, player=None):
    """Display a character as directly requested by a user."""
    try:
        owner = await common.player_lookup(ctx, player)
        tip = "`/character display` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        await display(ctx, character,
            owner=player,
            message=message,
            footer=None,
            traits_button=True
        )

    except LookupError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except common.FetchError:
        pass


async def __list_text(ctx, owner, characters):
    """List characters in plain text."""
    if ctx.author == owner:
        contents = ["Your Characters:\n"]
    else:
        contents = [f"{owner.display_name}'s Characters:\n"]

    contents.extend(characters)
    contents.append("```To view one: /character display character:NAME```")

    await ctx.respond("\n".join(contents), hidden=False)


async def __list_embed(ctx, owner, characters):
    """List characters in an embed."""
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


async def display(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None,
    traits_button: bool = False,
    color: int = None,
    thumbnail: str = None,
    components: list = None
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
        traits_button (bool): Whether to show a traits button. Default false
    """
    if Settings.accessible(ctx.author):
        msg = await __display_text(ctx, character,
            title=title,
            message=message,
            footer=footer,
            owner=owner,
            fields=fields,
            custom=custom,
            traits_button=traits_button,
            components=components
        )
    else:
        msg = await __display_embed(ctx, character,
            title=title,
            message=message,
            footer=footer,
            owner=owner,
            fields=fields,
            custom=custom,
            traits_button=traits_button,
            color=color,
            thumbnail=thumbnail,
            components=components
        )

    if traits_button:
        try:
            btn = await msg.wait_for("button", ctx.bot, timeout=60)
            while btn.author != ctx.author:
                await btn.respond("Sorry, you can't view these traits.", hidden=True)
                btn = await msg.wait_for("button", ctx.bot, timeout=60)

            await traits.show(btn, character.name, owner)
            await msg.disable_components()

        except asyncio.exceptions.TimeoutError:
            await msg.disable_components()
    else:
        return msg


async def __display_embed(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None,
    traits_button: bool = False,
    color: int = None,
    thumbnail: str = None,
    components: list = None
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
            ("Bane Severity", SEVERITY),
            ("Experience (Unspent / Lifetime)", EXPERIENCE)
        ]

    # Begin building the embed
    embed = discord.Embed(
        title=title or character.name,
        description=message or "",
        color=color or discord.Embed.Empty
    )

    author_name = owner.display_name if title is None else character.name
    embed.set_author(name=author_name, icon_url=owner.display_avatar)
    embed.set_footer(text=footer or "")

    if thumbnail is not None:
        embed.set_thumbnail(url=thumbnail)

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
        elif parameter == SEVERITY:
            if character.splat != "vampire":
                continue
            value = f"```{character.bane_severity}```"
        elif parameter == EXPERIENCE:
            value = "```\n"
            value += f"{character.current_xp} / {character.total_xp}\n"
            value += "```"

        embed.add_field(name=field, value=value, inline=False)

    if custom is not None:
        for field, value in custom:
            embed.add_field(name=field, value=value, inline=False)

    if traits_button:
        components = components or []
        components.append(Button("Traits", "traits"))

    return await ctx.respond(embed=embed, components=components)


async def __display_text(
    ctx,
    character: VChar,
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None,
    traits_button: bool = False,
    components: list = None
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
            ("Bane Severity", SEVERITY),
            ("Experience (Unspent / Lifetime)", EXPERIENCE)
        ]

    # Begin drafting the contents
    contents = [character.name]
    if title is not None:
        contents.append("\n" + title)

    if message is not None:
        contents.append(message)

    contents.append("```json") # Blank line

    for field, parameter in fields:
        if parameter == HEALTH:
            contents.append(f"{field}: {__stringify_track(character.health)}")
        elif parameter == WILLPOWER:
            contents.append(f"{field}: {__stringify_track(character.willpower)}")
        elif parameter == HUMANITY:
            contents.append(f"{field}: {character.humanity}")
            contents.append(f"Stains: {character.stains}")
        elif parameter == POTENCY:
            if character.splat != "vampire":
                continue
            contents.append(f"{field}: {character.potency}")
        elif parameter == HUNGER:
            if character.splat != "vampire":
                continue
            contents.append(f"{field}: {character.hunger}")
        elif parameter == SEVERITY:
            if character.splat != "vampire":
                continue
            contents.append(f"Bane Severity: {character.bane_severity}")
        elif parameter == EXPERIENCE:
            contents.append(f"{field}: {character.current_xp} / {character.total_xp}")

    if custom is not None:
        contents.append("")
        for field, value in custom:
            contents.append(f"{field}: {value}")

    contents.append("```")
    contents = "\n".join(contents)
    if footer is not None:
        contents += f"\n*{footer}*"

    if traits_button:
        components = components or []
        components.append(Button("Traits", "traits"))

    return await ctx.respond(contents, components=components)


def __stringify_track(track: str):
    """Convert a track into a textual representation."""
    agg = track.count(DAMAGE.aggravated)
    sup = track.count(DAMAGE.superficial)
    unh = track.count(DAMAGE.none)

    representation = []
    if agg > 0:
        representation.append(f"{agg} Agg")
    if sup > 0:
        representation.append(f"{sup} Sup")
    if unh > 0:
        representation.append(f"{unh} Unhurt")

    return " / ".join(representation)
