"""Transfer character ownership."""

import discord

import errors
import services
import ui
from ctx import AppCtx


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
                await ctx.bot.transfer_premium(new_owner, xfer)
            except errors.DuplicateCharacterError as err:
                await ui.embeds.error(ctx, str(err))
        else:
            await ui.embeds.error(ctx, f"{current_owner.display_name} doesn't own {xfer.name}!")

    except errors.CharacterNotFoundError:
        await ui.embeds.error(ctx, "Character not found.")
    except (LookupError, ValueError) as err:
        await ui.embeds.error(ctx, err)
