"""delete.py - Character deletion facilities."""

import asyncio

import discord
from discord_ui import Button

from .. import common
from ..vchar import errors, VChar


async def prompt(ctx, character: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)
        embed = __generate_prompt(ctx, character.name)

        buttons = [
            Button("_cancel", "Cancel", "secondary"),
            Button("_delete", f"Delete {character.name}", "red")
        ]
        msg = await ctx.respond(embed=embed, components=buttons, hidden=True)

        # Await the response
        try:
            btn = await msg.wait_for("button", ctx.bot, timeout=20)
            await btn.respond()
            await msg.disable_components()

            # Process the response
            if btn.custom_id == "_delete":
                if character.delete_character():
                    await ctx.respond(f"Deleted **{character.name}**!", hidden=True)
                else:
                    await ctx.respond("Something went wrong. Unable to delete.", hidden=True)

            else:
                await ctx.respond("Deletion canceled.", hidden=True)

        except asyncio.exceptions.TimeoutError:
            await msg.edit(content="**Deletion canceled due to inactivity.**")
            await msg.disable_components()

    except errors.UnspecifiedCharacterError:
        chars = [char.name for char in VChar.all_characters(ctx.guild.id, ctx.author.id)]
        err = "You must specify a character.\n\n**Options:**\n" + "\n".join(chars)
        await common.display_error(ctx, ctx.author.display_name, err)
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)


def __generate_prompt(ctx, char_name: str):
    """Send a fancy deletion embed."""
    embed = discord.Embed(
        title=f"Delete {char_name}",
        color=0xFF0000
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    embed.add_field(name="Are you certain?", value="This will delete all associated traits.")
    embed.set_footer(text="THIS ACTION CANNOT BE UNDONE")

    return embed
