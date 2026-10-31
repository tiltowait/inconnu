"""macros/show.py - Displaying character macros."""

from typing import NamedTuple

from discord.ui import Container, Separator, TextDisplay, Thumbnail

import errors
import ui
from ctx import AppCtx
from models import VChar
from services.haven import haven
from utils import get_avatar
from utils.text import paginate
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/macros#macro-list")


class MacroField(NamedTuple):
    """A text block describing a macro."""

    name: str
    value: str


def _has_macros(character: VChar):
    """Raises an error if the character has no macros."""
    if not character.macros:
        raise errors.MacroError(f"{character.name} has no macros!")


@haven(__HELP_URL, _has_macros, "None of your characters have any macros!")
async def show(ctx: AppCtx, character: VChar):
    """Show all of a character's macros."""
    macros = character.macros
    if not macros:
        await ui.embeds.error(
            ctx, f"{character.name} has no macros!", character=character.name, help=__HELP_URL
        )
        return

    await __display_macros(ctx, character, macros)


async def __display_macros(ctx: AppCtx, character: VChar, macros):
    """Show a user their character's macros, one container per page."""
    fields = __generate_fields(macros)
    raw_pages = paginate(1200, *fields)

    macro_roll = ctx.bot.cmd_mention("vm")
    macro_create = ctx.bot.cmd_mention("macro create")
    macro_update = ctx.bot.cmd_mention("macro update")
    macro_delete = ctx.bot.cmd_mention("macro delete")

    instructions = (
        "### Usage\n"
        f"**Roll:** {macro_roll}\n"
        f"**Create:** {macro_create}\n"
        f"**Update:** {macro_update}\n"
        f"**Delete:** {macro_delete}"
    )

    _pages = []
    for page in raw_pages:
        container = Container()
        container.add_section(
            TextDisplay(f"## Macros: {character.name}\n{instructions}"),
            accessory=Thumbnail(character.profile_image_url or get_avatar(ctx.user).url),
        )

        for field in page:
            container.add_item(Separator())
            container.add_item(TextDisplay(f"### {field.name}\n{field.value}"))

        _pages.append([container])

    await ctx.respond(view=ui.views.PagedView(_pages), ephemeral=True)


def __generate_fields(macros):
    """Convert macro records into human-readable fields."""
    fields = []

    for macro in macros:
        pool = f"`{' '.join(macro.pool)}`" if macro.pool else "*None*"
        value = f"**Pool:** {pool}\n**Hunger:** " + ("`Yes`" if macro.hunger else "`No`")
        value += f"\n**Difficulty:** `{macro.difficulty}`"
        value += f"\n**Rouse checks:** `{macro.rouses}`"
        if macro.rouses > 0:
            value += "\n**Re-rolling Rouses:** " + ("`Yes`" if macro.reroll_rouses else "`No`")
            value += "\n**Staining:** " + ("`Yes`" if macro.staining == "apply" else "`No`")
        value += "\n**Hunt:** " + ("`Yes`" if macro.hunt else "`No`")
        value += f"\n**Comment:** `{macro.comment or 'None'}`"

        fields.append(MacroField(name=macro.name.upper(), value=value))

    return fields
