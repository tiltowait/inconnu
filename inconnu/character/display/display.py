"""character/display/display.py - Tools for displaying characters."""
# pylint: disable=too-many-arguments

from enum import Enum

import discord

import inconnu
from inconnu.character.display import trackmoji
from inconnu.constants import Damage
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/displaying"

# Display fields


class DisplayField(str, Enum):
    """An enum for displaying character trackers."""

    HEALTH = "Health"
    WILLPOWER = "Willpower"
    HUMANITY = "Humanity"
    POTENCY = "Blood Potency"
    HUNGER = "Hunger"
    SEVERITY = "Bane Severity"
    EXPERIENCE = "Experience (Unspent / Lifetime)"

    @classmethod
    def all(cls):
        """Return a mapping of all (value, case) pairings."""
        return map(lambda f: (f.value, f), list(cls))


@haven(__HELP_URL)
async def display_requested(ctx, character, message=None, player=None, ephemeral=False):
    """Display a character as directly requested by a user."""
    await display(
        ctx,
        character,
        owner=player,
        message=message,
        footer=None,
        view=inconnu.views.TraitsView(character, ctx.user),
        ephemeral=ephemeral,
        thumbnail=character.profile_image_url,
    )


async def display(
    ctx,
    character: "VChar",
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None,
    color: int = None,
    thumbnail: str = None,
    view: discord.ui.View = None,
    ephemeral: bool = False,
    **kwargs,
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
    embed = await __get_embed(
        ctx,
        character,
        title=title,
        message=message,
        footer=footer,
        owner=owner,
        fields=fields,
        custom=custom,
        color=color,
        thumbnail=thumbnail,
    )
    msg_contents = {"embed": embed}
    if view is not None:
        msg_contents["view"] = view

    if not kwargs.get("edit_message", False):
        msg_contents["ephemeral"] = ephemeral
        msg = await ctx.respond(**msg_contents)

        if isinstance(view, inconnu.views.DisablingView):
            view.message = msg

        return msg

    # We are editing the original message
    if view is None:
        # We need to remove the view
        msg_contents["view"] = None
    elif isinstance(view, inconnu.views.DisablingView):
        view.message = ctx.message
    return await ctx.message.edit(**msg_contents)


async def __get_embed(
    ctx,
    character: "VChar",
    title: str = None,
    message: str = None,
    footer: str = None,
    owner: discord.Member = None,
    fields: list = None,
    custom: list = None,
    color: int = None,
    thumbnail: str = None,
):
    # Set the default values
    owner = owner or ctx.user
    fields = fields or DisplayField.all()

    # Begin building the embed
    title = title or character.name
    if title == character.name:
        profile_url = inconnu.profile_url(character.id)
    else:
        profile_url = discord.Embed.Empty

    embed = discord.Embed(
        title=title,
        description=message or "",
        color=color or discord.Embed.Empty,
        url=profile_url,
    )

    embed.set_author(
        name=owner.display_name if title is None else character.name,
        icon_url=inconnu.get_avatar(owner),
    )
    embed.set_footer(text=footer or discord.Embed.Empty)
    embed.set_thumbnail(url=thumbnail or discord.Embed.Empty)

    can_emoji = await inconnu.settings.can_emoji(ctx)

    for field, parameter in fields:
        # We use optionals because ghouls and mortals don't have every parameter
        if (value := __embed_field_value(character, parameter, can_emoji)) is not None:
            embed.add_field(name=field, value=value, inline=False)

    if custom is not None:
        for field, value in custom:
            embed.add_field(name=field, value=value, inline=False)

    return embed


def __embed_field_value(character, parameter, can_emoji):
    """Generates the value for a given embed field."""
    value = None

    match parameter:
        case DisplayField.HEALTH:
            value = __stat_repr(can_emoji, trackmoji.emojify_track, character.health)

        case DisplayField.WILLPOWER:
            value = __stat_repr(can_emoji, trackmoji.emojify_track, character.willpower)

        case DisplayField.HUMANITY:
            value = __stat_repr(
                can_emoji, trackmoji.emojify_humanity, character.humanity, character.stains
            )

        case DisplayField.POTENCY if character.is_vampire:
            value = __stat_repr(can_emoji, trackmoji.emojify_blood_potency, character.potency)

        case DisplayField.HUNGER if character.is_vampire:
            value = __stat_repr(can_emoji, trackmoji.emojify_hunger, character.hunger)

        case DisplayField.SEVERITY if character.is_vampire:
            value = f"```{character.bane_severity}```"

        case DisplayField.EXPERIENCE:
            value = f"```{character.experience.unspent} / {character.experience.lifetime}```"

    return value


def __stat_repr(can_emoji, function, *stats):
    """Generate the string or emoji representation of a stat, depending on permissions."""
    if len(stats) == 2:
        # Humanity
        humanity, stains = stats

        if can_emoji:
            return function(humanity, stains)

        stains = inconnu.common.pluralize(stains, "Stain")

        return f"{humanity} ({stains})"

    # Not Humanity
    stat = stats[0]

    if can_emoji:
        return function(stat)

    if isinstance(stat, str):
        return __stringify_track(stat)

    # The stat should be an int
    return stat


def __stringify_track(track: str):
    """Convert a track into a textual representation."""
    agg = track.count(Damage.AGGRAVATED)
    sup = track.count(Damage.SUPERFICIAL)
    unh = track.count(Damage.NONE)

    representation = []
    if unh > 0:
        representation.append(f"{unh} Unhurt")
    if sup > 0:
        representation.append(f"{sup} Sup")
    if agg > 0:
        representation.append(f"{agg} Agg")

    return " / ".join(representation)
