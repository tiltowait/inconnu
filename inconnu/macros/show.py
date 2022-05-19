"""macros/show.py - Displaying character macros."""

from types import SimpleNamespace

import discord
from discord.ext import pages

import inconnu

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=retrieval"


async def show(ctx, character=None):
    """Show all of a character's macros."""
    try:
        tip = "`/macro list` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)

        # We have a valid character
        macros = character.macros
        if not macros:
            await inconnu.common.present_error(
                ctx,
                f"{character.name} has no macros!",
                character=character.name,
                help_url=__HELP_URL,
            )
            return

        await __display_macros(ctx, character.name, macros)

    except inconnu.common.FetchError:
        pass


async def __display_macros(ctx, char_name, macros):
    """Show a user their character's macros in an embed."""
    fields = __generate_fields(macros, False)
    raw_pages = inconnu.common.paginate(1200, *fields)

    _pages = []
    for page in raw_pages:
        embed = discord.Embed(title="Macros")
        embed.set_author(name=char_name, icon_url=inconnu.get_avatar(ctx.user))
        embed.set_footer(text="To roll a macro, use the /vm command.")

        for field in page:
            embed.add_field(name=field.name, value=field.value, inline=False)

        _pages.append(embed)

    paginator = pages.Paginator(pages=_pages, show_disabled=False)
    await paginator.respond(ctx.interaction, ephemeral=True)


def __generate_fields(macros, accessible: bool):
    """Convert macro records into human-readable fields."""
    fields = []

    for macro in macros:
        pool = " ".join(macro.pool)
        value = f"**Pool:** `{pool}`\n**Hunger:** " + ("`Yes`" if macro.hunger else "`No`")
        value += f"\n**Difficulty:** `{macro.difficulty}`"
        value += f"\n**Rouse checks:** `{macro.rouses}`"
        if macro.rouses > 0:
            value += "\n**Re-rolling Rouses:** " + ("`Yes`" if macro.reroll_rouses else "`No`")
            value += "\n**Staining:** " + ("`Yes`" if macro.staining == "apply" else "`No`")
        value += "\n**Hunt:** " + ("`Yes`" if macro.hunt else "`No`")
        value += f"\n**Comment:** `{macro.comment or 'None'}`"

        fields.append(SimpleNamespace(name=macro.name.upper(), value=value))

    return fields
