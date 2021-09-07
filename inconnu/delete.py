"""delete.py - Character deletion facilities."""

import asyncio

import discord
from discord_ui import Button

from .databases import CharacterNotFoundError
from .constants import character_db


async def prompt(ctx, char_name: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        char_name, char_id = character_db.character(ctx.guild.id, ctx.author.id, char_name)
        embed = __generate_prompt(ctx, char_name)

        buttons = [
            Button("_cancel", "Cancel", "secondary"),
            Button("_delete", f"Delete {char_name}", "red")
        ]
        msg = await ctx.respond(embed=embed, components=buttons, hidden=True)

        # Await the response
        try:
            btn = await msg.wait_for("button", ctx.bot, timeout=20)
            await btn.respond()
            await msg.delete()

            # Process the response
            if btn.custom_id == "_delete":
                if character_db.delete_character(ctx.guild.id, ctx.author.id, char_id):
                    await ctx.respond(f"Deleted {char_name}!", hidden=True)
                else:
                    await ctx.respond("Something went wrong. Unable to delete.", hidden=True)

            else:
                await ctx.respond("Deletion canceled.", hidden=True)

        except asyncio.exceptions.TimeoutError:
            await msg.edit(content="**Deletion canceled due to inactivity.**")
            await msg.disable_components()

    except CharacterNotFoundError as err:
        await ctx.respond(str(err), hidden=True)


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
