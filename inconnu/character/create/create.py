"""character/create/create.py - Handle new character creation."""
# pylint: disable=too-many-arguments

import re
from types import SimpleNamespace as SN

import inconnu
from . import wizard

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-creation"


async def create(ctx, name: str, splat: str, humanity: int, health: int, willpower: int, spc: bool):
    """Parse and handle character creation arguments."""
    if spc and not ctx.user.guild_permissions.administrator:
        await inconnu.common.present_error(
            ctx, "You need Administrator permissions to make an SPC."
        )
        return

    try:
        __validate_parameters(name, humanity, health, willpower) # splat is guaranteed correct

        # Remove extraenous spaces from the name
        name = re.sub(r"\s+", " ", name)

        if await inconnu.char_mgr.exists(ctx.guild, ctx.user, name, spc):
            if spc:
                raise ValueError(f"Sorry, there is already an SPC named `{name}`!")
            raise ValueError(f"Sorry, you have a character named `{name}` already!")

        parameters = SN(name=name, hp=health, wp=willpower, humanity=humanity, splat=splat, spc=spc)
        accessibility = await inconnu.settings.accessible(ctx.user)
        character_wizard = wizard.Wizard(ctx, parameters, accessibility)

        await character_wizard.begin_chargen()

    except ValueError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


def __validate_parameters(name, humanity, health, willpower):
    """
    Determines whether the user supplied valid chargen arguments.
    Raises a ValueError with all user mistakes.
    """
    errors = []

    if (name_len := len(name)) > 30:
        errors.append(f"`{name}` is too long by {name_len - 30} characters.")

    if re.match(r"^[A-z_\s\d-]+$", name) is None:
        errors.append("Character names may only contain letters, spaces, hyphens, and underscores.")

    if not 0 <= humanity <= 10:
        errors.append(f"Humanity must be between 0 and 10. (Got `{humanity}`)")

    if not 4 <= health <= 15:
        errors.append(f"Health must be between 4 and 15. (Got `{health}`)")

    if not 3 <= willpower <= 15:
        errors.append(f"Willpower must be between 3 and 15. (Got `{willpower}`)")

    if errors:
        err = "\n".join(errors)
        raise ValueError(err)
