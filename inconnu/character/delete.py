"""delete.py - Character deletion facilities."""

import asyncio

import discord
from discord_ui import Button

from .. import common
from ..settings import Settings
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-deletion"


async def delete(ctx, character: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
        buttons = [
            Button("Cancel", "_cancel", "secondary"),
            Button(f"Delete {character.name}", "_delete", "red")
        ]
        msg = await __prompt(ctx, character.name, buttons)

        # Await the response
        btn = await msg.wait_for("button", ctx.bot, timeout=20)
        await msg.disable_components()

        # Process the response
        if btn.custom_id == "_delete":
            if character.delete_character():
                await btn.respond(f"Deleted **{character.name}**!")
            else:
                await btn.respond("Something went wrong. Unable to delete.", hidden=True)

        else:
            await btn.respond("Deletion canceled.", hidden=True)

    except errors.CharacterError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)
    except asyncio.exceptions.TimeoutError:
        await msg.edit(
            content="**Deletion canceled due to inactivity.**",
            components=None,
            embed=None
        )


async def __prompt(ctx, char_name: str, buttons):
    """Send a fancy deletion embed."""
    if Settings.accessible(ctx.author):
        return await __prompt_text(ctx, char_name, buttons)

    return await __prompt_embed(ctx, char_name, buttons)


async def __prompt_text(ctx, char_name: str, buttons):
    """Ask the user whether to delete the character, in plain text."""
    contents = f"Really delete {char_name}? This will delete all associated data!\n"
    return await ctx.respond(contents, components=buttons, hidden=True)


async def __prompt_embed(ctx, char_name: str, buttons):
    """Ask the user whether to delete the character, using an embed."""
    embed = discord.Embed(
        title=f"Delete {char_name}",
        color=0xFF0000
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
    embed.add_field(name="Are you certain?", value="This will delete all associated data.")
    embed.set_footer(text="THIS ACTION CANNOT BE UNDONE")

    return await ctx.respond(embed=embed, components=buttons, hidden=True)
