"""Delete an RP post message chain."""

import discord

import inconnu


async def delete_message_chain(ctx: discord.ApplicationContext, message: discord.Message):
    """Delete an RP post, its header, and its mentions."""
    # Uses the general WebhookError handler
    webhook = await ctx.bot.prep_webhook(ctx.channel)

    try:
        rp_post = await _fetch_rp_post(ctx, webhook, message)
        await ctx.send_modal(DeletionModal(webhook, rp_post))

    except ValueError as err:
        await inconnu.utils.error(ctx, err, title="Invalid message")


async def _fetch_rp_post(
    ctx: discord.ApplicationContext, webhook: discord.Webhook, message: discord.Message
) -> inconnu.models.rppost.RPPost:
    """Validate the message and ownership, displaying an error message if applicable."""
    if not message.author.bot:
        raise ValueError("You can't delete a user's post.")

    if message.author.id == ctx.bot.user.id:
        raise ValueError("This isn't an RP post!")

    if webhook.id != message.author.id:
        raise ValueError("Either this isn't an RP post, or the original webhook was deleted.")

    rp_post = await inconnu.models.RPPost.find_one({"id_chain": message.id})
    if rp_post is None:
        if await inconnu.db.headers.find_one({"message": message.id}) is not None:
            raise ValueError("Use `Header: Delete` for this.")
        raise ValueError("Something went wrong. Ask a moderator to delete the message for you.")

    # We found an RP post, but we need to check ownership
    if rp_post.user != ctx.user.id:
        raise ValueError("This isn't your RP post!")

    return rp_post


class DeletionModal(discord.ui.Modal):
    """A modal that asks for confirmation before deleting the post chain."""

    def __init__(self, webhook: discord.Webhook, rp_post: inconnu.models.RPPost, *args, **kwargs):
        self.webhook = webhook
        self.rp_post = rp_post

        super().__init__(title="Delete RP post?", *args, **kwargs)

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
        if self.children[0].value.lower() == "delete":
            await interaction.response.defer(ephemeral=True, invisible=False)
            for msg_id in self.rp_post.id_chain:
                try:
                    await self.webhook.delete_message(msg_id)
                except (discord.HTTPException, discord.Forbidden):
                    # The only way an error should occur is if one of the message
                    # chain was already deleted. We should have permission to
                    # delete our own messages, so we can just ignore this error.
                    pass
            await interaction.respond("RP post deleted!", delete_after=3)

        else:
            await inconnu.utils.error(
                interaction, "You must type `DELETE` to delete.", title="Invalid response"
            )
