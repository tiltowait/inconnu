"""macros/show.py - Displaying character macros."""

import asyncio
from types import SimpleNamespace

import discord

from .. import common
from ..settings import Settings

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=retrieval"


async def show(ctx, character=None):
    """Show all of a character's macros."""
    try:
        tip = "`/macro list` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)

        # We have a valid character
        macros = character.macros
        if len(macros) == 0:
            await common.present_error(
                ctx,
                f"{character.name} has no macros!",
                character=character.name,
                help_url=__HELP_URL
            )
            return

        await __display_macros(ctx, character.name, macros)

    except common.FetchError:
        pass


async def __display_macros(ctx, char_name, macros):
    """Show a user their character's macros."""
    if Settings.accessible(ctx.author):
        await __macro_text(ctx, char_name, macros)
    else:
        await __macro_embed(ctx, char_name, macros)


async def __macro_text(ctx, char_name, macros):
    """Show a user their character's macros in an embed."""
    fields = __generate_fields(macros, True)
    pages = common.paginate(1200, *fields)

    for page_num, page in enumerate(pages):
        if (page_count := len(pages)) == 1:
            contents = [f"{char_name}'s Macros\n"]
        else:
            contents = [f"{char_name}'s Macros: Page {page_num + 1} of {page_count}\n"]

        for field in page:
            contents.append(f"```{field.name}```")
            contents.append(field.value + "\n")

        await ctx.respond("\n".join(contents), ephemeral=True)
        await asyncio.sleep(0.5)


async def __macro_embed(ctx, char_name, macros):
    """Show a user their character's macros in an embed."""
    fields = __generate_fields(macros, False)
    pages = common.paginate(1200, *fields)

    for page_num, page in enumerate(pages):
        page_text = f"Page {page_num + 1} of {len(pages)}"

        embed = discord.Embed(
            title="Macros" if len(pages) == 1 else f"Macros: {page_text}"
        )
        embed.set_author(name=char_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text=page_text)

        for field in page:
            embed.add_field(name=field.name, value=field.value, inline=False)

        await ctx.respond(embed=embed, ephemeral=True)
        await asyncio.sleep(0.5)


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
