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
                help_url=__HELP_URL
            )
            return

        await __display_macros(ctx, character.name, macros)

    except inconnu.common.FetchError:
        pass


async def __display_macros(ctx, char_name, macros):
    """Show a user their character's macros."""
    if await inconnu.settings.accessible(ctx.user):
        await __macro_text(ctx, char_name, macros)
    else:
        await __macro_embed(ctx, char_name, macros)


async def __macro_text(ctx, char_name, macros):
    """Show a user their character's macros in an embed."""
    fields = __generate_fields(macros, True)
    raw_pages = inconnu.common.paginate(1200, *fields)

    _pages = []
    for page in raw_pages:
        contents = [f"**{char_name}'s Macros**\n"]

        for field in page:
            contents.append(f"```{field.name}```")
            contents.append(field.value + "\n")

        _pages.append("\n".join(contents))

    paginator = pages.Paginator(pages=_pages, show_disabled=False)
    await paginator.respond(ctx.interaction, ephemeral=True)


async def __macro_embed(ctx, char_name, macros):
    """Show a user their character's macros in an embed."""
    fields = __generate_fields(macros, False)
    raw_pages = inconnu.common.paginate(1200, *fields)

    _pages = []
    for page in raw_pages:
        embed = discord.Embed(title="Macros")
        embed.set_author(name=char_name, icon_url=ctx.user.display_avatar)
        embed.set_footer(text="To roll a macro, use the /vm command")

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
        if accessible:
            value = f"Pool: `{pool}`\nHunger: " + ("`Yes`" if macro.hunger else "`No`")
            if macro.difficulty > 0:
                value += f"\nDifficulty: `{macro.difficulty}`"
            if macro.rouses > 0:
                value += f"\nRouse checks: `{macro.rouses}`"
                value += "\nRe-rolling Rouses: " + ("`Yes`" if macro.reroll_rouses else "`No`")
            if macro.comment is not None:
                value += f"\nComment: `{macro.comment}`"
        else:
            value = f"**Pool:** `{pool}`\n**Hunger:** " + ("`Yes`" if macro.hunger else "`No`")
            if macro.difficulty > 0:
                value += f"\n**Difficulty:** `{macro.difficulty}`"
            if macro.rouses > 0:
                value += f"\n**Rouse checks:** `{macro.rouses}`"
                value += "\n**Re-rolling Rouses:** " + ("`Yes`" if macro.reroll_rouses else "`No`")
                value += "\n**Staining:** " + ("`Yes`" if macro.staining == "apply" else "`No`")
            if macro.comment is not None:
                value += f"\n**Comment:** `{macro.comment}`"

        fields.append(SimpleNamespace(name=macro.name.upper(), value=value))

    return fields
