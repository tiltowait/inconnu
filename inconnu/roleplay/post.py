"""Tupperbox-style character posting."""

import re

import discord

import inconnu
from inconnu.utils.haven import haven
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/"


class PostModal(discord.ui.Modal):
    """A modal for getting post details."""

    DIVIDER = "\n" + " " * 30 + "\n\n"  # Ogham space mark: \u1680

    def __init__(self, character: inconnu.models.VChar, bot, *args, **kwargs):
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
            self.header = inconnu.models.HeaderSubdoc.create(character, **header_params)
            starting_value = ""
            starting_title = ""
            starting_tags = ""
        else:
            self.header = self.post_to_edit.header
            starting_value = self.post_to_edit.content
            starting_title = self.post_to_edit.title
            starting_tags = "; ".join(self.post_to_edit.tags)

        # Populate the modal
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Post details",
                placeholder="Your RP post",
                value=starting_value,
                min_length=1,
                max_length=2000,
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

    def _clean_post_content(self) -> str:
        """Clean and attempt to normalize the post content."""
        lines = self.children[0].value.split("\n")
        cleaned = [inconnu.utils.clean_text(line) for line in lines if line]
        return "\n\n".join(cleaned)

    def _clean_title(self) -> str:
        """Clean the title."""
        return inconnu.utils.clean_text(self.children[-2].value)

    def _clean_tags(self) -> list[str]:
        """Clean and separate the tags."""
        raw_tags = self.children[-1].value.lower().replace(",", ";")
        tags = re.sub(r"[^\w\s;]+", "", raw_tags)
        tags = tags.split(";")

        cleaned_tags = []
        for tag in tags:
            if cleaned := inconnu.utils.clean_text(tag):
                cleaned_tags.append(cleaned)

        return sorted(list(set(cleaned_tags)))  # Make sure the tags are unique

    async def callback(self, interaction: discord.Interaction):
        """Set the RP post content."""
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
                await inconnu.utils.error(
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
        await self.post_to_edit.commit()

        await interaction.response.send_message("Post updated!", ephemeral=True, delete_after=3)
        Logger.info("POST: %s edited a post (%s)", self.character.name, self.message.id)

        if post_to_changelog:
            await self._post_to_changelog(interaction)

    async def _new_rp_post(self, interaction: discord.Interaction):
        """Make a new RP post."""
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

        content = self._clean_post_content()
        content_message = await webhook.send(
            content=content,
            username=self.character.name,
            avatar_url=webhook_avatar,
            wait=True,
        )

        id_chain = [content_message.id]
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
            Logger.info("POST: %s registered header", self.character.name)

        # Extract the user mentions as pure ints
        mention_ids = []
        for mention in self.mentions.split():
            if match := re.search(r"<@!?(\d+)>", mention):
                try:
                    mention_ids.append(int(match.group(1)))
                except ValueError:
                    # This shouldn't ever happen, but just in case
                    continue

        # Register the RP post
        db_rp_post = inconnu.models.RPPost.create(
            interaction=interaction,
            character=self.character,
            header=self.header,
            content=content,
            message=content_message,
            mentions=mention_ids,
            title=self._clean_title() or None,
            tags=self._clean_tags(),
        )
        db_rp_post.id_chain = id_chain
        await db_rp_post.commit()

        Logger.info("POST: %s registered post", self.character.name)

    async def _post_to_changelog(self, interaction: discord.Interaction):
        """Post the edited message to the RP changelog."""
        if changelog_id := await inconnu.settings.changelog_channel(interaction.guild):
            # Prep the diff
            post = self.post_to_edit
            diff = inconnu.utils.diff(post.history[0].content, post.content)

            # Prep the embed
            description = (
                f"{interaction.user.mention} edited a post in <#{post.channel}>."
                "\n```diff\n"
                f"{diff}\n"
            )
            description = description[:3996] + "```"  # Ensure we don't overflow

            embed = discord.Embed(
                title="RP Post Edited",
                description=description,
                url=inconnu.post_url(post.pk),
            )
            embed.set_author(
                name=post.header.char_name, icon_url=inconnu.get_avatar(interaction.user)
            )
            embed.set_thumbnail(url=self.character.profile_image_url)
            embed.add_field(name=" ", value=f"[Jump to message.]({post.url})")
            embed.timestamp = discord.utils.utcnow()

            # Prep the channel and send
            changelog = interaction.client.get_partial_messageable(changelog_id)
            try:
                await changelog.send(embed=embed)
                Logger.info("POST: Sent changelog to %s: %s", interaction.guild.name, changelog_id)
            except discord.HTTPException:
                Logger.info(
                    "POST: Changelog channel doesn't exist: %s: %s",
                    interaction.guild.name,
                    changelog_id,
                )
            except discord.Forbidden:
                Logger.info(
                    "POST: Unable to post changelog in %s: %s",
                    interaction.guild.name,
                    changelog_id,
                )
        else:
            Logger.debug("POST: Changelog channel not set: %s", interaction.guild.name)


@haven(__HELP_URL, errmsg="You have no characters!")
async def create_post(ctx: discord.ApplicationContext, character: str, **kwargs):
    """Create a modal that sends an RP post."""
    modal = PostModal(character, ctx.bot, title=f"{character.name}'s Post", **kwargs)
    await ctx.send_modal(modal)


async def edit_post(ctx: discord.ApplicationContext, message: discord.Message):
    """Edit an RP post."""
    rp_post = await inconnu.models.RPPost.find_one({"message_id": message.id})

    # Need to perform some checks to ensure we can edit the post
    if rp_post is None:
        await inconnu.utils.error(ctx, "This isn't a roleplay post!", help=__HELP_URL)
    elif ctx.user.id != rp_post.user:
        await inconnu.utils.error(ctx, "You can only edit your own posts!", help=__HELP_URL)
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
            await inconnu.utils.error(
                ctx,
                "You can't edit the post of a deleted character!",
                help=__HELP_URL,
            )
