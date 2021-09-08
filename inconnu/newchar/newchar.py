"""newchar.py - Handle new character creation."""

import re
from collections import namedtuple

from . import wizard
from ..constants import character_db
from .. import common

Parameters = namedtuple('Parameters', ["name", "hp", "wp", "humanity", "type"])


async def create(ctx, name: str, splat: str, humanity: int, health: int, willpower: int):
    """Parse and handle character creation arguments."""
    try:
        __validate_parameters(name, humanity, health, willpower) # splat is guaranteed correct

        if await character_db.character_exists(ctx.guild.id, ctx.author.id, name):
            raise ValueError(f"Sorry, you have a character named `{name}` already!")

        await ctx.respond(
            "Please check your DMs! I hope you have your character sheet ready.",
            hidden=True
        )

        parameters = Parameters(name, health, willpower, humanity, splat)
        character_wizard = wizard.Wizard(ctx, parameters)
        await character_wizard.begin_chargen()

    except ValueError as err:
        await common.display_error(ctx, ctx.author.display_name, err)


def __validate_parameters(name, humanity, health, willpower):
    """
    Determines whether the user supplied valid chargen arguments.
    Raises a ValueError with all user mistakes.
    """
    errors = []

    if re.match(r"^[A-z_]+$", name) is None:
        errors.append("Character names may only contain letters and underscores.")

    if not 0 <= humanity <= 10:
        errors.append(f"Humanity must be between 0 and 10. (Got `{humanity}`)")

    if not 4 <= health <= 15:
        errors.append(f"Health must be between 4 and 15. (Got `{health}`)")

    if not 3 <= willpower <= 15:
        errors.append(f"Willpower must be between 3 and 15. (Got `{willpower}`)")

    if len(errors) > 0:
        err = "\n".join(errors)
        raise ValueError(err)
