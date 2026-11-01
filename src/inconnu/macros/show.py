"""macros/show.py - Displaying character macros."""

from typing import NamedTuple

from discord.ui import Container, Section, TextDisplay, Thumbnail

import errors
import ui
from ctx import AppCtx
from models import VChar
from models.vchardocs import VCharMacro
from services.haven import haven
from utils import get_avatar
from utils.text import pluralize
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/macros#macro-list")
__PAGE_CHARS = 1200
__PAGE_MACROS = 10  # Each macro costs two of a message's 40 components


class MacroField(NamedTuple):
    """A text block describing a macro."""

    name: str
    value: str
    comment: str | None


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


async def __display_macros(ctx: AppCtx, character: VChar, macros: list[VCharMacro]):
    """Show a user their character's macros, each in its own container."""
    fields = __generate_fields(macros)
    raw_pages = __paginate(fields)

    macro_roll = ctx.bot.cmd_mention("vm")
    macro_create = ctx.bot.cmd_mention("macro create")
    macro_update = ctx.bot.cmd_mention("macro update")
    macro_delete = ctx.bot.cmd_mention("macro delete")

    instructions = (
        f"-# Roll: {macro_roll}\n"
        f"-# Create: {macro_create}\n"
        f"-# Update: {macro_update}\n"
        f"-# Delete: {macro_delete}"
    )

    _pages = []
    for page in raw_pages:
        header = Section(
            TextDisplay(f"## Macros: {character.name}\n{instructions}"),
            accessory=Thumbnail(character.profile_image_url or get_avatar(ctx.user).url),
        )

        macro_containers = []
        for field in page:
            text = f"### {field.name}"
            if field.value:
                text += f"\n{field.value}"
            if field.comment:
                # A small blank line, shorter than an empty one
                text += f"\n-# \u200b\n-# {field.comment}"

            macro_containers.append(Container(TextDisplay(text)))

        _pages.append([header, *macro_containers])

    await ctx.respond(view=ui.views.PagedView(_pages), ephemeral=True)


def __paginate(fields: list[MacroField]) -> list[list[MacroField]]:
    """Split the fields into pages, limited by length and macro count."""
    pages: list[list[MacroField]] = [[]]
    page_len = 0
    for field in fields:
        if page_len >= __PAGE_CHARS or len(pages[-1]) == __PAGE_MACROS:
            pages.append([])
            page_len = 0
        pages[-1].append(field)
        page_len += len(field.name) + len(field.value) + len(field.comment or "")

    return pages


def __generate_fields(macros: list[VCharMacro]) -> list[MacroField]:
    """Convert macro records into human-readable fields. Only settings that
    differ from the defaults are shown."""
    fields = []

    for macro in macros:
        lines = []
        if macro.pool:
            lines.append(f"`{' '.join(macro.pool)}`")

        details = []
        if macro.difficulty > 0:
            details.append(f"Difficulty {macro.difficulty}")
        if macro.rouses > 0:
            rouses = pluralize(macro.rouses, "Rouse Check")
            if macro.reroll_rouses:
                rouses += " (rerolled)"
            details.append(rouses)
            if macro.staining == "apply":
                details.append("Stains")
        if not macro.hunger:
            details.append("No Hunger")
        if macro.hunt:
            details.append("Hunt")

        if details:
            lines.append(" · ".join(details))

        fields.append(MacroField(macro.name.upper(), "\n".join(lines), macro.comment))

    return fields
