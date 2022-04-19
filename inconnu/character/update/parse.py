"""character/update/parse.py - Defines an interface for updating character traits."""
# pylint: disable=too-many-arguments

import asyncio

import discord
from discord.ui import Button

import inconnu

from ...vchar import VChar
from ..display import display
from . import paramupdate

__MATCHES = {}

__KEYS = {
    "name": "The character's name",
    "health": "The character's max Health",
    "willpower": "The character's max Willpower",
    "humanity": "The character's Humanity",
    "splat": "The type of character: `vampire`, `mortal`, or `ghoul`",
    "sh": "+/- Superficial Health damage",
    "ah": "+/- Aggravated Health damage",
    "sw": "+/- Superficial Willpower damage",
    "aw": "+/- Aggravated Willpower damage",
    "stains": "+/- Stains",
    "unspent_xp": "+/- Unspent XP",
    "lifetime_xp": "+/- Total Lifetime XP",
    "hunger": "+/- The character's Hunger",
    "potency": "+/- The character's Blood Potency",
}

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=tracker-updates"


async def update(
    ctx, parameters: str, character=None, fields=None, color=None, update_message=None, player=None
):
    """
    Process the user's arguments.
    Allow the user to omit a character if they have only one.
    """
    if not parameters:
        # Might have got here through a help message
        await update_help(ctx)
        return

    parameters = " ".join(parameters.split())

    # This will get overwritten, but we need it now in case we run into trouble
    # trying to parse the input
    human_readable = parameters

    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = f"`/character update` `parameters:{parameters}` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        parameters = inconnu.utils.parse_parameters(parameters, True)
        human_readable = " ".join([f"{k}={v}" for k, v in parameters.items()])
        parameters = __validate_parameters(parameters)
        updates = []

        for parameter, new_value in parameters.items():
            update_msg = await __update_character(ctx, character, parameter, new_value)
            updates.extend(update_msg.split("\n"))

        if (impairment := character.impairment) is not None:
            updates.append(impairment)

        tasks = [
            inconnu.log.log_event(
                "update",
                user=ctx.user.id,
                guild=ctx.guild.id,
                charid=character.id,
                syntax=human_readable,
            )
        ]

        # Ignore generated output if we got a custom message
        if update_message is None:
            update_message = "\n".join(map(lambda u: f"• {u}", updates))  # Give them bullet points

        tasks.append(
            display(
                ctx,
                character,
                fields=fields,
                color=color,
                owner=player,
                message=update_message,
                thumbnail=character.image_url if not fields else None,
            )
        )

        _, inter = await asyncio.gather(*tasks)
        if update_message:  # May not always be true in the future
            msg = await inconnu.get_message(inter)
            await inconnu.common.report_update(
                ctx=ctx,
                msg=msg,
                character=character,
                title="Character Updated",
                message=f"__{ctx.user.mention} updated {character.name}:__\n" + update_message,
            )

    except (SyntaxError, ValueError) as err:
        log_task = inconnu.log.log_event(
            "update_error",
            user=ctx.user.id,
            guild=ctx.guild.id,
            charid=character.id,
            syntax=human_readable,
        )
        help_task = update_help(ctx, err)
        await asyncio.gather(log_task, help_task)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


def __validate_parameters(parameters):
    """Validate the user's parameters."""
    validated = {}

    for key, value in parameters.items():
        if (key := __MATCHES.get(key.lower())) is None:
            raise ValueError(f"Unknown parameter: `{key}`.")

        if key in validated:
            # We already checked with the raw input, but they may have used
            # sh and sd, for instance, which map to the same thing
            raise ValueError(f"You cannot use `{key}` more than once.")

        if not value:
            raise ValueError(f"Missing value for key `{key}`.")

        validated[key] = value

    return validated


async def __update_character(ctx, character: VChar, param: str, value: str) -> str:
    """
    Update one of a character's parameters.
    Args:
        character (VChar): The character being updated
        param (str): The parameter to update
        value (str): The parameter's new value
    Raises ValueError if the parameter's value is invalid.
    """
    if param == "current_xp":
        if not await inconnu.settings.can_adjust_current_xp(ctx):
            raise ValueError("You must have administrator privileges to adjust unspent XP.")
    elif param == "total_xp":
        if not await inconnu.settings.can_adjust_lifetime_xp(ctx):
            raise ValueError("You must have administrator privileges to adjust lifetime XP.")

    coro = getattr(paramupdate, f"update_{param}")
    return await coro(character, value)


async def update_help(ctx, err=None, ephemeral=True):
    """Display a help message that details the available keys."""
    color = discord.Embed.Empty if err is None else 0xFF0000
    embed = discord.Embed(title="Character Tracking", color=color)
    embed.set_author(name=ctx.user.display_name, icon_url=inconnu.get_avatar(ctx.user))

    if err is not None:
        embed.add_field(name="Error", value=str(err), inline=False)

    inst = "To update a character, use `/character update` with one or more `KEY=VALUE` pairs."
    embed.add_field(name="Instructions", value=inst, inline=False)

    parameters = [f"***{key}:*** {val}" for key, val in __KEYS.items()]
    parameters = "\n".join(parameters)
    embed.add_field(name="Keys", value=parameters, inline=False)
    embed.add_field(
        name="Example",
        value="Character takes 4 Superficial Health damage:```/character update parameters:sh+4```",
    )

    embed.set_footer(text="You may modify more than one tracker at a time.")

    documentation = Button(
        label="Full Documentation",
        url="http://www.inconnu-bot.com/#/character-tracking?id=tracker-updates",
    )
    support = Button(label="Support", url=inconnu.constants.SUPPORT_URL)
    view = discord.ui.View(documentation, support)

    await inconnu.respond(ctx)(embed=embed, view=view, ephemeral=ephemeral)


# We do flexible matching for the keys. Many of these are the same as RoD's
# keys, while others have been observed in syntax error logs. This should be
# a little more user-friendly.


def __setup_matches():
    """Register all the update keys."""
    __register_keys("name")
    __register_keys("health", "hp")
    __register_keys("willpower", "wp", "w")
    __register_keys("humanity", "hm")
    __register_keys("splat", "type")
    __register_keys(
        "sh", "sd", "shp", "suphp", "suph", "supd", "superficialhealth", "superficialdamage"
    )
    __register_keys("ah", "ad", "ahp", "agghp", "aggd", "aggh", "agghealth", "aggdamage")
    __register_keys("sw", "swp", "supwp", "supw", "superficialwillpower")
    __register_keys("aw", "awp", "aggwp", "aggw", "aggwillpower")
    __register_keys("stains", "stain", "s")
    __register_keys(
        "current_xp",
        "xp_current",
        "current_exp",
        "exp_current",
        "currentxp",
        "currentexp",
        "xpcurrent",
        "expcurrent",
        "cxp",
        "unspent_xp",
        "xp_unspent",
        "unspent_exp",
        "exp_unspent",
        "unspentxp",
        "unspentexp",
        "xpunspent",
        "expunspent",
        "uxp",
    )
    __register_keys(
        "total_xp",
        "xp_total",
        "total_exp",
        "exp_total",
        "totalxp",
        "totalexp",
        "xptotal",
        "exptotal",
        "txp",
        "lifetimexp",
        "xplifetime",
        "explifetime",
        "lxp",
        "lifetime_xp",
        "life_time_xp",
    )
    __register_keys("hunger", "h")
    __register_keys("potency", "bp", "p")


def __register_keys(canonical, *alternates):
    """Register an update key along with some alternates."""
    __MATCHES[canonical] = canonical
    for alternate in alternates:
        if alternate in __MATCHES:
            raise KeyError(f"{alternate} is already an update parameter.")
        __MATCHES[alternate] = canonical


__setup_matches()
