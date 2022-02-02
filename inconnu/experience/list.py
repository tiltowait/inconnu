"""experience/list.py - List XP expenditures/gains."""

import discord

import inconnu


__HELP_URL = "https://www.inconnu-bot.com"


async def list_events(ctx, character, player):
    """List a character's XP events."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience list character:CHARACTER player:PLAYER`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        msg = { "ephemeral": player.id == ctx.user.id }
        if inconnu.settings.accessible(ctx.user):
            await ctx.respond("Text not yet implemented.", ephemeral=True)
        else:
            msg["embed"] = await __get_embed(ctx, character, player)

        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**msg)
            else:
                await ctx.response.send_message(**msg)
        else:
            await ctx.respond(**msg)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


async def __get_embed(ctx, character, player):
    """Make an embed in which to display the XP events."""
    embed = discord.Embed(
        title=f"{character.name}'s Experience Log",
        description=await __get_contents(ctx, character)
    )
    embed.set_author(name=player.display_name, icon_url=player.display_avatar)
    embed.add_field(
        name="Experience (Unspent / Lifetime)",
        value=f"```{character.current_xp} / {character.total_xp}```"
    )

    return embed


async def __get_contents(ctx, character):
    """Get the event contents used by both embeds and text."""
    events = character.experience_log
    date_format = "%b %d, %Y"

    contents = []
    for event in events:
        date = event["date"].strftime(date_format)
        exp = event["amount"]
        reason = event["reason"]
        admin_id = event["admin"]

        # Get the admin discord.Member. Try the cache first.
        if (admin := ctx.guild.get_member(admin_id)) is None:
            print("Couldn't find in the cache")
            admin = await ctx.guild.fetch_member(admin_id)

        text = f"__**{exp:+}:** {reason}__ *({date}, @{admin.display_name})*"
        #text = f"`{exp:+}` by @{admin.display_name}: `{reason}` *({date})*"
        #text = f"**{date}:** `{exp:+}` by @{admin.display_name}: {reason}"
        #if text[-1] != ".":
        #    text += "."

        contents.append(text)

    if not contents:
        contents.append("*No experince awards/deductions have been logged.*")

    return "\n".join(contents)
