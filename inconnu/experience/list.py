"""experience/list.py - List XP expenditures/gains."""

from datetime import timezone

import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com"


async def list_events(ctx, character, player, ephemeral):
    """List a character's XP events."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience list character:CHARACTER player:PLAYER`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        msg = {"ephemeral": ephemeral}
        if await inconnu.settings.accessible(ctx):
            msg["content"] = await __get_text(ctx, character)
        else:
            msg["embed"] = await __get_embed(ctx, character, owner)

        mentions = discord.AllowedMentions(users=False)
        await inconnu.respond(ctx)(**msg, allowed_mentions=mentions)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


async def __get_embed(ctx, character, player):
    """Make an embed in which to display the XP events."""
    embed = discord.Embed(title="Experience Log", description=await __get_contents(ctx, character))
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
    embed.add_field(
        name="Experience (Unspent / Lifetime)",
        value=f"```{character.current_xp} / {character.total_xp}```",
    )

    return embed


async def __get_text(ctx, character):
    """Get the text-mode version of the XP log."""
    contents = [f"**{character.name}'s Experience Log**\n"]
    contents.append(await __get_contents(ctx, character))
    contents.append(f"\n**New XP:** {character.current_xp} / {character.total_xp}")

    return "\n".join(contents)


async def __get_contents(ctx, character):
    """Get the event contents used by both embeds and text."""
    events = character.experience_log

    contents = []
    for index, event in enumerate(reversed(events)):
        # We need the date/time to be TZ-aware
        date = event["date"]
        date = date.replace(tzinfo=timezone.utc)
        date = inconnu.gen_timestamp(date, "d")

        exp = event["amount"]
        reason = event["reason"]
        admin_id = event["admin"]
        scope = event["event"].split("_")[-1]

        # Get the admin discord.Member. Try the cache first.
        if (admin := ctx.guild.get_member(admin_id)) is None:
            admin = await ctx.guild.fetch_member(admin_id)

        text = f"*{index + 1}.* **{exp:+} {scope}: {reason}** - {admin.mention} • {date}"

        contents.append(text)

    if not contents:
        contents.append("*No experience awards/deductions have been logged.*")

    return "\n".join(contents)
