"""experience/remove.py - Remove an XP log entry."""

import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com"


async def remove_entry(ctx, player, character, index):
    """Award or deduct XP from a character."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience remove player:PLAYER character:CHARACTER index:INDEX`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        try:
            log = character.experience_log
            entry_to_delete = log[-index] # Log entries are presented to the user in reverse
            character.remove_experience_log_entry(entry_to_delete)

            if inconnu.settings.accessible(ctx.user):
                msg = { "content": _get_text(character, entry_to_delete) }
            else:
                msg = { "embed": _get_embed(owner, character, entry_to_delete) }

            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(**msg)
                else:
                    await ctx.response.send_message(**msg)
            else:
                await ctx.respond(**msg)

        except IndexError:
            err = f"{character.name} has no experience log entry at index `{index}`."
            await inconnu.common.present_error(ctx, err)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


def _get_embed(player, character, entry):
    """Generate an embed for displaying the deletion message."""
    embed = discord.Embed(
        title="Deleted Experience Log Entry",
        description=_format_event(entry)
    )
    embed.set_author(name=character.name, icon_url=player.display_avatar)
    embed.set_footer(text="Be sure to adjust unspent/lifetime XP accordingly!")

    return embed


def _get_text(character, entry):
    """Generate text version of deletion message."""
    msg = f"**{character.name}**\n"
    msg += "```Deleted Experience Log Entry```"
    msg += "\n" + _format_event(entry)
    msg += "\n\n*Be sure to adjust unspent/lifetime XP accordingly!"

    return msg


def _format_event(entry):
    """Format the deleted entry for display."""
    date = entry["date"].strftime("%b %d, %Y")
    scope = entry["event"].split("_")[-1].capitalize()

    return f"**{entry['amount']:+} {scope} XP: {entry['reason']}** *({date})*"
