"""common.py - Commonly used functions."""

import discord

# TODO: Re-adapt this

#async def character_options_message(guildid: int, userid: int, input_name: str) -> str:
#    """Create a message informing the user they need to supply a correct character."""
 #   user_chars = list(await character_db.characters(guildid, userid).keys())
  #  message = None
#
#    if len(user_chars) == 0:
 #       message = "You have no characters!"
  #  else:
   #     user_chars = list(map(lambda char: f"`{char}`", user_chars))
    #    message = f"You have no character named `{input_name}`. Options:\n\n"
     #   message += ", ".join(user_chars)
#
#    return message


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes"}

    pluralized = f"{value} {noun}"
    if value != 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized


async def display_error(ctx, char_name, error):
    """Display an error in a nice embed."""
    embed = discord.Embed(
        title="Error",
        description=str(error),
        color=0xFF0000
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    if hasattr(ctx, "reply"):
        await ctx.reply(embed=embed)
    else:
        await ctx.respond(embed=embed, hidden=True)
