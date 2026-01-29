"""character/update/parse.py - Defines an interface for updating character traits."""

import asyncio
from collections import OrderedDict

import discord
from discord.ui import Button

import inconnu
import services
from ctx import AppCtx
from inconnu.character.display import DisplayField, display
from inconnu.character.update import paramupdate
from models import VChar
import ui.views

__MATCHES = {}

__KEYS = {
    "name": "The character's name",
    "health": "The character's max Health",
    "willpower": "The character's max Willpower",
    "humanity": "The character's Humanity",
    "splat": "The type of character: `vampire`, `mortal`, `ghoul`, or `thinblood`",
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

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/updates"


async def update(
    ctx: AppCtx,
    parameters: str,
    character: "VChar | str | None" = None,
    fields: list[DisplayField] | None = None,
    color: discord.Color | None = None,
    update_message: str | None = None,
    player: discord.Member | None = None,
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
        haven = services.Haven(
            ctx,
            character=character,
            owner=player,
            tip=f"`/character update` `parameters:{parameters}` `character:CHARACTER`",
            help=__HELP_URL,
        )
        character = await haven.fetch()

        parameters = inconnu.utils.parse_parameters(parameters, True)
        human_readable = " ".join([f"{k}={v}" for k, v in parameters.items()])
        parameters = __validate_parameters(parameters)
        updates = []

        for parameter, new_value in parameters.items():
            update_msg = await __update_character(ctx, character, parameter, new_value)
            if "(Hint:" in update_msg:
                # Hints only show up in errors, so let's make the embed red
                color = discord.Color.red() if not color else color
            updates.extend(update_msg.split("\n"))

        if (impairment := character.impairment) is not None:
            updates.append(impairment)

        tasks = [
            character.save(),
            inconnu.log.log_event(
                "update",
                user=ctx.user.id,
                guild=ctx.guild.id,
                charid=character.id_str,
                syntax=human_readable,
            ),
        ]

        # Ignore generated output if we got a custom message
        if update_message is None:
            update_message = "\n".join(map(lambda u: f"* {u}", updates))  # Give them bullet points

        tasks.append(
            display(
                ctx,
                character,
                fields=fields,
                color=color,
                owner=haven.owner,
                message=update_message,
                thumbnail=character.profile_image_url if not fields else None,
            )
        )

        _, _, inter = await asyncio.gather(*tasks)
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
        if isinstance(character, VChar):
            character.rollback()

            await asyncio.gather(
                inconnu.log.log_event(
                    "update_error",
                    user=ctx.user.id,
                    guild=ctx.guild.id,
                    charid=character.id_str,
                    syntax=human_readable,
                ),
                update_help(ctx, err),
                # character.reload(),  # clear_modified() doesn't reset the fields
            )


def __validate_parameters(parameters):
    """Validate the user's parameters."""
    validated = OrderedDict()

    for key_, value in parameters.items():
        if (key := __MATCHES.get(key_.lower())) is None:
            raise ValueError(f"Unknown parameter: `{key_}`.")

        if key in validated:
            # We already checked with the raw input, but they may have used
            # sh and sd, for instance, which map to the same thing
            raise ValueError(f"You cannot use `{key}` more than once.")

        if not value:
            raise ValueError(f"Missing value for key `{key}`.")

        validated[key] = value

    return validated


async def __update_character(ctx, character: "VChar", param: str, value: str) -> str:
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
    elif param == "name":
        # This is the only async method
        return await paramupdate.update_name(character, value)

    func = getattr(paramupdate, f"update_{param}")
    return func(character, value)


async def update_help(ctx, err=None, ephemeral=True):
    """Display a help message that details the available keys."""
    color = None if err is None else 0xFF0000
    embed = discord.Embed(title="Character Tracking", color=color)
    embed.set_author(name=inconnu.bot.user.display_name)
    embed.set_thumbnail(url=inconnu.bot.user.avatar)

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
        url="https://docs.inconnu.app/command-reference/characters/updates",
    )
    support = Button(label="Support", url=inconnu.constants.SUPPORT_URL)
    view = ui.views.ReportingView(documentation, support)

    await ctx.respond(embed=embed, view=view, ephemeral=ephemeral)


# We do flexible matching for the keys. Many of these are the same as RoD's
# keys, while others have been observed in syntax error logs. This should be
# a little more user-friendly.


def __setup_matches():
    """Register all the update keys."""
    __register_keys("name")
    __register_keys("health", "hp")
    __register_keys("willpower", "wp", "w")
    __register_keys("humanity", "hm")
    __register_keys("splat", "type", "template")
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
