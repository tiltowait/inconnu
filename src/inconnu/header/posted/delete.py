"""Delete a posted RP header."""

import discord
from loguru import logger

import db
import errors
from ctx import AppCtx
from utils.permissions import is_approved_user


async def delete_header(ctx: AppCtx, message: discord.Message):
    """Validate ownership and delete a posted RP header."""
    try:
        webhook = await ctx.bot.prep_webhook(message.channel)
        is_bot_message = message.author == ctx.bot.user
        is_webhook_message = message.author.id == webhook.id
    except (errors.WebhookError, ValueError):
        webhook = None
        is_bot_message = message.author == ctx.bot.user
        is_webhook_message = False

    if not is_bot_message and not is_webhook_message:
        await ctx.respond("This is not an RP header.", ephemeral=True)
        return

    record = await db.headers.find_one({"message": message.id})
    if record is None:
        await ctx.respond("This is not an RP header.", ephemeral=True)
        return

    owner = record["character"]["user"]
    if not is_approved_user(ctx, owner=owner):
        logger.debug("Unauthorized header deletion attempt by {}", ctx.user.name)
        await ctx.respond("You don't have permission to delete this RP header.", ephemeral=True)
        return

    try:
        if is_bot_message:
            logger.debug("Deleting header via message.delete()")
            await message.delete()
        else:
            logger.debug("Deleting header via webhook.delete_message()")
            await webhook.delete_message(message.id)
        await ctx.respond("RP header deleted!", ephemeral=True, delete_after=3)
    except discord.errors.Forbidden:
        await ctx.respond(
            "Something went wrong. Unable to delete the header. This may be a permissions issue.",
            ephemeral=True,
        )
        logger.warning(
            "Unable to delete header {} in #{} on {}",
            record["message"],
            ctx.channel.name,
            ctx.guild.name,
        )
