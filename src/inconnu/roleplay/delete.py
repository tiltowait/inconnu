"""Rolepost deletion handlers."""

from typing import Any

import discord

import db
import errors
import ui
from ctx import AppCtx
from models import RPPost
from utils.urls import post_url


async def delete_message_chain(ctx: AppCtx, message: discord.Message):
    """Delete a Rolepost, its header, and its mentions."""
    # Uses the general WebhookError handler
    try:
        webhook = await ctx.bot.prep_webhook(ctx.channel)
        rp_post = await _fetch_rp_post(ctx, webhook, message)
        await ctx.send_modal(DeletionModal(webhook, rp_post))

    except (errors.WebhookError, ValueError) as err:
        await ui.embeds.error(ctx, err, title="Invalid message")


async def _fetch_rp_post(ctx: AppCtx, webhook: discord.Webhook, message: discord.Message) -> RPPost:
    """Validate the message and ownership, displaying an error message if applicable."""
    if not message.author.bot:
        raise ValueError("You can't delete a user's post.")

    if message.author == ctx.bot.user:
        raise ValueError("This isn't a Rolepost!")

    if webhook.id != message.author.id:
        raise ValueError("Either this isn't a Rolepost, or the original webhook was deleted.")

    rp_post = await RPPost.find_one({"id_chain": message.id})
    if rp_post is None:
        if await db.headers.find_one({"message": message.id}) is not None:
            raise ValueError("Use `Header: Delete` for this.")
        raise ValueError("Something went wrong. Ask a moderator to delete the message for you.")

    # We found a Rolepost, but we need to check ownership
    if rp_post.user != ctx.user.id:
        raise ValueError("This isn't your Rolepost!")

    return rp_post


def deletion_embed(post: RPPost) -> discord.Embed:
    """The deletion channel's notice for a Rolepost."""
    if post.id is None:
        raise ValueError("Rolepost has not been saved")

    return discord.Embed(
        title="Post Deleted",
        description=(
            f"**Poster:** <@{post.user}>\n"
            f"**Channel:** <#{post.channel}>\n"
            f"**Content:**\n\n{post.content}"
        ),
        url=post_url(post.id),
        color=discord.Color.red(),
        timestamp=post.utc_date,
    )


class DeletionModal(discord.ui.Modal):
    """A modal that asks for confirmation before deleting the post chain."""

    def __init__(self, webhook: discord.Webhook, rp_post: RPPost, *args: Any, **kwargs: Any):
        self.webhook = webhook
        self.rp_post = rp_post

        super().__init__(title="Delete Rolepost?", *args, **kwargs)

        self.add_item(
            discord.ui.InputText(
                label="Delete your post?",
                placeholder="Type DELETE to confirm, or press cancel",
                style=discord.InputTextStyle.short,
                max_length=6,
                required=True,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Check the input."""
        if (self.children[0].value or "").lower() == "delete":
            await interaction.response.defer(ephemeral=True, invisible=False)
            for msg_id in self.rp_post.id_chain:
                try:
                    await self.webhook.delete_message(msg_id)
                except discord.HTTPException, discord.Forbidden:
                    # The only way an error should occur is if one of the message
                    # chain was already deleted. We should have permission to
                    # delete our own messages, so we can just ignore this error.
                    pass
            await interaction.respond("Rolepost deleted!", delete_after=3)

        else:
            await ui.embeds.error(
                interaction, "You must type `DELETE` to delete.", title="Invalid response"
            )
