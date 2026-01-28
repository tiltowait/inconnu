"""Tupperbox-style character posting."""

import re

import discord
from loguru import logger

import inconnu
from models import HeaderSubdoc, RPPost, VChar
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/"


class PostModal(discord.ui.Modal):
    """A modal for getting post details."""

    SECTIONS = 2

    def __init__(self, character: VChar, bot, *args, **kwargs):
        self.character = character
        self.bot = bot  # Used for webhook management
        self.post_to_edit = kwargs.pop("rp_post", None)
        self.message = kwargs.pop("message", None)
        self.mentions = " ".join(inconnu.utils.pull_mentions(kwargs.pop("mentions", "")))
        self.show_header = kwargs.pop("show_header", True)

        if self.post_to_edit is None:
            header_params = {
                param: kwargs.pop(param, None)
                for param in ["blush", "location", "merits", "flaws", "temp", "hunger"]
            }
            self.header = HeaderSubdoc.create(character, **header_params)
            starting_value = ""
            starting_title = ""
            starting_tags = ""
        else:
            self.header = self.post_to_edit.header
            starting_value = self.post_to_edit.content
            starting_title = self.post_to_edit.title
            starting_tags = "; ".join(self.post_to_edit.tags)

        # Populate the modal
        post_len = 2000 if self.post_to_edit else 4000
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Message",
                placeholder="Enter your post here.",
                value=starting_value,
                min_length=1,
                max_length=post_len,
                style=discord.InputTextStyle.long,
            )
        )
        if self.post_to_edit is None:
            for _ in range(PostModal.SECTIONS - 1):
                self.add_item(
                    discord.ui.InputText(
                        label="Message (cont)",
                        placeholder="Use if your post is too long to fit the first textbox.",
                        value=starting_value,
                        max_length=post_len,
                        required=False,
                        style=discord.InputTextStyle.long,
                    )
                )
        self.add_item(
            discord.ui.InputText(
                label="Bookmark title",
                placeholder="(Optional) A title for easy bookmarking",
                value=starting_title,
                max_length=128,
                style=discord.InputTextStyle.short,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Tags",
                placeholder="(Optional) Separate with ;",
                value=starting_tags,
                max_length=128,
                style=discord.InputTextStyle.short,
                required=False,
            )
        )

    def _clean_post_content(self) -> str | list[str]:
        """Clean and attempt to normalize the post content."""
        if self.post_to_edit is None:
            contents = [
                child.value for child in self.children[0 : PostModal.SECTIONS] if child.value
            ]
            return inconnu.utils.re_paginate(contents)
        return inconnu.utils.re_paginate([self.children[0].value])[0]

    def _clean_title(self) -> str:
        """Clean the title."""
        return inconnu.utils.clean_text(self.children[-2].value)

    def _clean_tags(self) -> list[str]:
        """Clean and separate the tags."""
        raw_tags = self.children[-1].value.lower().replace(",", ";")
        tags = re.sub(r"[^\w\s;\(\)]+", "", raw_tags)
        tags = tags.split(";")

        cleaned_tags = []
        for tag in tags:
            if cleaned := inconnu.utils.clean_text(tag):
                cleaned_tags.append(cleaned)

        return sorted(list(set(cleaned_tags)))  # Make sure the tags are unique

    async def callback(self, interaction: discord.Interaction):
        """Set the Rolepost content."""
        if self.post_to_edit is None:
            await self._new_rp_post(interaction)
        else:
            await self._edit_rp_post(interaction)

    async def _edit_rp_post(self, interaction: discord.Interaction):
        """Edit an existing post."""
        new_content = self._clean_post_content()
        post_to_changelog = False

        if new_content != self.post_to_edit.content:
            post_to_changelog = True
            # We have a WebhookMessage, so we need to fetch its originating
            # Webhook, which is the only entity that can edit it. We keep this
            # call outside of the try block so we can use our general Webhook
            # error checker.
            webhook = await self.bot.prep_webhook(interaction.channel)
            try:
                await webhook.edit_message(self.message.id, content=new_content)
                self.post_to_edit.edit_post(new_content)

            except discord.NotFound:
                await inconnu.embeds.error(
                    interaction,
                    (
                        "The message wasn't found. Either someone deleted it while you "
                        "were editing, or else the webhook that created it was deleted."
                    ),
                    title="Unable to edit message",
                )
                return

        # Finish updating the post and inform the user
        self.post_to_edit.title = self._clean_title() or None
        self.post_to_edit.tags = self._clean_tags()
        await self.post_to_edit.save()

        await interaction.response.send_message("Post updated!", ephemeral=True, delete_after=3)
        logger.info("POST: {} edited a post ({})", self.character.name, self.message.id)

        if post_to_changelog:
            await self._post_to_changelog(interaction)

    async def _new_rp_post(self, interaction: discord.Interaction):
        """Make a new Rolepost."""
        # We need an interaction response, so make and delete this one
        await interaction.response.send_message("Posting!", ephemeral=True, delete_after=1)

        webhook = await self.bot.prep_webhook(interaction.channel)
        webhook_avatar = self.character.profile_image_url or inconnu.get_avatar(interaction.user)

        if self.show_header:
            # We take a regular header embed as a base, then modify it ... a lot
            header_embed = inconnu.header.embed(self.header, self.character, True)
            header_embed.description += f"\n*Author: {interaction.user.mention}*"

            header_message = await webhook.send(
                embed=header_embed,
                username=self.character.name,
                avatar_url=webhook_avatar,
                wait=True,
            )
        else:
            header_message = None

        contents = self._clean_post_content()
        post_messages = []
        id_chain = []
        for page in contents:
            msg = await webhook.send(
                content=page,
                username=self.character.name,
                avatar_url=webhook_avatar,
                wait=True,
            )
            post_messages.append(msg)

            # The ID chain has all message IDs, not just the current post's ID
            id_chain.append(msg.id)

        if self.show_header:
            id_chain.insert(0, header_message.id)

        if self.mentions:
            mention_message = await webhook.send(
                content=self.mentions,
                username=self.character.name,
                avatar_url=webhook_avatar,
                wait=True,
            )
            id_chain.append(mention_message.id)

        # Register the messages
        if self.show_header:
            await inconnu.header.register(interaction, header_message, self.character)
            logger.info("POST: {} registered header", self.character.name)

        # Extract the user mentions as pure ints
        mention_ids = []
        for mention in self.mentions.split():
            if match := re.search(r"<@!?(\d+)>", mention):
                try:
                    mention_ids.append(int(match.group(1)))
                except ValueError:
                    # This shouldn't ever happen, but just in case
                    continue

        # Register the Rolepost
        title = self._clean_title() or None
        tags = self._clean_tags()
        for content, message in zip(contents, post_messages):
            db_rp_post = RPPost.new(
                interaction=interaction,
                character=self.character,
                header=self.header,
                content=content,
                message=message,
                mentions=mention_ids,
                title=title,
                tags=tags,
            )
            db_rp_post.id_chain = id_chain
            await db_rp_post.save()

            # We only want to save the tags and bookmark for the first post
            title = None
            tags = []

        logger.info("POST: {} registered post", self.character.name)

    async def _post_to_changelog(self, interaction: discord.Interaction):
        """Post the edited message to the RP changelog."""
        if changelog_id := await inconnu.settings.changelog_channel(interaction.guild):
            # Prep the diff
            post = self.post_to_edit
            diff = inconnu.utils.diff(post.history[0].content, post.content)

            # Prep the embed
            description = (
                f"{interaction.user.mention} edited a post in <#{post.channel}>.\n```diff\n{diff}\n"
            )
            description = description[:3996] + "```"  # Ensure we don't overflow

            embed = discord.Embed(
                title="Rolepost Edited",
                description=description,
                url=inconnu.post_url(post.id),
            )
            embed.set_author(
                name=post.header.char_name, icon_url=inconnu.get_avatar(interaction.user)
            )
            embed.set_thumbnail(url=self.character.profile_image_url)
            embed.add_field(name=" ", value=post.url)
            embed.timestamp = self.post_to_edit.utc_date

            # Prep the channel and send
            changelog = interaction.client.get_partial_messageable(changelog_id)
            try:
                await changelog.send(embed=embed)
                logger.info("POST: Sent changelog to {}: {}", interaction.guild.name, changelog_id)
            except discord.HTTPException:
                logger.info(
                    "POST: Changelog channel doesn't exist: {}: {}",
                    interaction.guild.name,
                    changelog_id,
                )
            except discord.Forbidden:
                logger.info(
                    "POST: Unable to post changelog in {}: {}",
                    interaction.guild.name,
                    changelog_id,
                )
        else:
            logger.debug("POST: Changelog channel not set: {}", interaction.guild.name)


@haven(__HELP_URL)
async def create_post(ctx: discord.ApplicationContext, character: str, **kwargs):
    """Create a modal that sends a Rolepost."""
    if ctx.bot.can_webhook(ctx.channel):
        modal = PostModal(character, ctx.bot, title=f"{character.name}'s Post", **kwargs)
        await ctx.send_modal(modal)
    elif isinstance(ctx.channel, discord.threads.Thread):
        await inconnu.embeds.error(ctx, "This command is unavailable in threads.")
    else:
        await inconnu.embeds.error(
            ctx,
            "This feature requires `Manage Webhooks` permission.",
            title="Missing permissions",
        )


async def edit_post(ctx: discord.ApplicationContext, message: discord.Message):
    """Edit a Rolepost."""
    rp_post = await RPPost.find_one({"message_id": message.id})

    # Need to perform some checks to ensure we can edit the post
    if rp_post is None:
        await inconnu.embeds.error(ctx, "This isn't a Rolepost!", help=__HELP_URL)
    elif ctx.user.id != rp_post.user:
        await inconnu.embeds.error(ctx, "You can only edit your own posts!", help=__HELP_URL)
    else:
        # It's a valid post, but we can only work our magic if the character
        # still exists. Otherwise, spit out an error.
        try:
            character = await inconnu.char_mgr.fetchone(
                ctx.guild_id,
                ctx.user.id,
                str(rp_post.header.charid),
            )
            modal = PostModal(
                character,
                ctx.bot,
                title=f"Edit {rp_post.header.char_name}'s Post",
                rp_post=rp_post,
                message=message,
            )
            await ctx.send_modal(modal)

        except inconnu.errors.CharacterNotFoundError:
            await inconnu.embeds.error(
                ctx,
                "You can't edit the post of a deleted character!",
                help=__HELP_URL,
            )
