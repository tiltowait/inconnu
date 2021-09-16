"""macros/show.py - Displaying character macros."""

from types import SimpleNamespace

import discord

from .. import common
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/macros?id=retrieval"


async def show(ctx, character=None):
    """Show all of a character's macros."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
    except errors.UnspecifiedCharacterError as err:
        tip = "`/macro list` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
        return

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

    await __send_macros(ctx, character.name, macros)


async def __send_macros(ctx, char_name, macros):
    """Show a user their character's macros."""
    embed = discord.Embed(
        title="Macros"
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    for field in __generate_fields(macros):
        embed.add_field(name=field.name, value=field.value, inline=False)

    await ctx.respond(embed=embed, hidden=True)


def __generate_fields(macros):
    """Convert macro records into human-readable fields."""
    fields = []

    for macro in macros:
        pool = " ".join(macro.pool)
        value = f"**Pool:** `{pool}`"
        if macro.difficulty > 0:
            value += f"\n**Difficulty:** *{macro.difficulty}*"
        if macro.comment is not None:
            value += f"\n**Comment:** *{macro.comment}*"

        fields.append(SimpleNamespace(name=macro.name.upper(), value=value))

    return fields
