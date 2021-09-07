"""macros/show.py - Displaying character macros."""

from collections import namedtuple

import discord

from .. import common
from . import macro_common

MacroField = namedtuple("MacroField", ["name", "value"])

async def process(ctx, character=None):
    """Show all of a character's macros."""
    char_name, char_id = common.get_character(ctx.guild.id, ctx.author.id, character)

    if char_name is None:
        message = common.character_options_message(ctx.guild.id, ctx.author.id, character)
        await common.display_error(ctx, ctx.author.display_name, message)
        return

    # We have a valid character.
    macros = await macro_common.macro_db.char_macros(char_id)

    if len(macros) == 0:
        await common.display_error(ctx, char_name, f"{char_name} has no macros!")
        return

    await __send_macros(ctx, char_name, macros)


async def __send_macros(ctx, char_name, macros):
    """Show a user their character's macros."""
    embed = discord.Embed(
        title="Macros"
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    for field in __generate_fields(macros):
        embed.add_field(name=field.name, value=field.value)

    await ctx.respond(embed=embed, hidden=True)


def __generate_fields(macros):
    """Convert macro records into human-readable fields."""
    fields = []

    for macro in macros:
        name = macro["name"].upper()
        pool = " ".join(macro["pool"])
        difficulty = macro["diff"]
        comment = macro["comment"]

        value = f"**Pool:** *{pool}*"
        if difficulty > 0:
            value += f"\n**Difficulty:** *{difficulty}*"
        if comment is not None:
            value += f"\n**Comment:** *{comment}*"

        fields.append(MacroField(name, value))

    return fields
