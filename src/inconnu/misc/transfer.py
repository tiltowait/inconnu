"""Transfer character ownership."""

from datetime import timedelta

import discord
from loguru import logger

import constants
import errors
import services
import ui
from ctx import AppCtx
from models import VChar
from services.premium import GRACE_PERIOD
from utils.text import pluralize


async def transfer_character(
    ctx: AppCtx,
    current_owner: discord.Member,
    character: str,
    new_owner: discord.Member,
):
    """Reassign a character from one player to another."""
    if current_owner.id == new_owner.id:
        await ui.embeds.error(ctx, "`current_owner` and `new_owner` can't be the same.")
        return

    try:
        assert ctx.guild is not None  # Guild context guarantees this
        xfer = await services.char_mgr.fetchone(ctx.guild, current_owner, character)

        if ctx.guild.id == xfer.guild and current_owner.id == xfer.user:
            current_mention = current_owner.mention
            new_mention = new_owner.mention

            try:
                await services.char_mgr.transfer(xfer, current_owner, new_owner)
                await ctx.respond(
                    f"Transferred **{xfer.name}** from {current_mention} to {new_mention}."
                )
                await _warn_if_deletion(new_owner, xfer)
            except errors.DuplicateCharacterError as err:
                await ui.embeds.error(ctx, str(err))
        else:
            await ui.embeds.error(ctx, f"{current_owner.display_name} doesn't own {xfer.name}!")

    except errors.CharacterNotFoundError:
        await ui.embeds.error(ctx, "Character not found.")
    except (errors.WrongGuild, errors.WrongOwner, ValueError) as err:
        await ui.embeds.error(ctx, err)


async def _warn_if_deletion(new_owner: discord.Member, character: VChar):
    """If the new owner isn't a supporter, DM them when their new character's
    images will be deleted. Starts their grace period if it hasn't begun."""
    if not character.profile.images:
        return
    lapsed = await services.premium.lapse_date(new_owner.id)
    if lapsed is None:
        logger.info("{} is a supporter; inheriting {}'s images", new_owner.name, character.name)
        return

    days_left = round((lapsed + GRACE_PERIOD - discord.utils.utcnow()) / timedelta(days=1))
    if days_left < 1:
        deadline = "within a day"
    else:
        deadline = f"in {pluralize(days_left, 'day')}"

    server = f"[Inconnu server]({constants.SUPPORT_URL})"
    patreon = f"[patron]({constants.PATREON})"
    embed = discord.Embed(
        title=f"{character.name} has profile images",
        description=(
            f"You aren't a {patreon}, so {character.name}'s images will be deleted "
            f"{deadline}. To keep them, join the {server} and become a {patreon}."
        ),
        color=discord.Color.red(),
    )

    try:
        await new_owner.send(embed=embed)
        logger.info("Warned {} that {}'s images will be deleted", new_owner.name, character.name)
    except discord.HTTPException:
        logger.info("Could not DM {} about {}'s images", new_owner.name, character.name)
