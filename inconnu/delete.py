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
        msg = await ctx.reply(embed=embed, components=buttons)

        # Await the response
        try:
            btn = await msg.wait_for("button", ctx.bot, timeout=20)
            await btn.respond()
            await msg.delete()

            # Process the response
            if btn.custom_id == "_delete":
                if character_db.delete_character(ctx.guild.id, ctx.author.id, char_id):
                    await ctx.reply(f"Deleted {char_name}!")
                else:
                    await ctx.reply("Something went wrong. Unable to delete.")

            else:
                await ctx.reply("Deletion canceled.")

        except asyncio.exceptions.TimeoutError:
            await msg.delete()
            await ctx.reply("You didn't respond within 20 seconds. Deletion canceled.")


    except CharacterNotFoundError as err:
        await ctx.reply(str(err))


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
