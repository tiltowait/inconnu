"""Tupperbox-style character posting."""

import discord

import inconnu
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/"


class PostModal(discord.ui.Modal):
    """A modal for getting post details."""

    DIVIDER = "\n" + " " * 30 + "\n\n"  # Ogham space mark: \u1680

    def __init__(self, character: inconnu.models.VChar, *args, **kwargs):
        self.character = character
        self.mention = kwargs.pop("mention", None)
        self.post_to_edit = kwargs.pop("rp_post", None)
        self.message = kwargs.pop("message", None)

        if self.post_to_edit is None:
            header_params = {
                param: kwargs.pop(param, None)
                for param in ["blush", "location", "merits", "flaws", "temp", "hunger"]
            }
            self.header = inconnu.models.HeaderSubdoc.create(character, **header_params)
            starting_value = ""
        else:
            self.header = self.post_to_edit.header
            starting_value = self.post_to_edit.content

        # We create a throwaway embed to determine the max possible post length
        embed = inconnu.header.embed(self.header, self.character)
        header_len = len(embed.description)

        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Post details",
                placeholder="Your RP post",
                value=starting_value,
                min_length=1,
                max_length=4000 - header_len - len(self.DIVIDER),  # 33 is from the divider
                style=discord.InputTextStyle.long,
            )
        )

    def _clean_post_content(self) -> str:
        """Clean and attempt to normalize the post content."""
        lines = self.children[0].value.split("\n")
        cleaned = [inconnu.utils.clean_text(line) for line in lines if line]
        return "\n\n".join(cleaned)

    def _create_embed(self, content: str) -> discord.Embed:
        """Create an RP post embed."""
        rp_post = inconnu.header.embed(self.header, self.character)
        rp_post.description += self.DIVIDER + content

        return rp_post

    async def callback(self, interaction: discord.Interaction):
        """Set the RP post content."""

        if self.post_to_edit is None:
            await self._new_rp_post(interaction)
        else:
            await self._edit_rp_post(interaction)

    async def _edit_rp_post(self, interaction: discord.Interaction):
        """Edit an existing post."""
        new_content = self._clean_post_content()
        new_rp_embed = self._create_embed(new_content)

        await self.message.edit(embed=new_rp_embed)

        # Update the RPPost object
        self.post_to_edit.edit_post(new_content)
        await self.post_to_edit.commit()
        Logger.info("POST: %s edited a post (%s)", self.character.name, self.message.id)

        # Inform the user
        await interaction.response.send_message("Post updated!", ephemeral=True)

    async def _new_rp_post(self, interaction: discord.Interaction):
        """Post a new RP post."""
        content = self._clean_post_content()

        # We will use a basic RP header as the base for our embed
        rp_post = self._create_embed(content)

        if self.mention:
            resp = await interaction.response.send_message(self.mention.mention, embed=rp_post)
        else:
            resp = await interaction.response.send_message(embed=rp_post)

        # Register the header
        message = await resp.original_response()
        await inconnu.header.register(interaction, message, self.character)
        Logger.info("POST: %s registered header", self.character.name)

        # Register the RP post
        db_rp_post = inconnu.models.RPPost.create(self.character, self.header, content, message)
        await db_rp_post.commit()

        Logger.info("POST: %s registered post", self.character.name)


async def create_post(ctx: discord.ApplicationContext, character: str, **kwargs):
    """Create a modal that sends an RP post."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = PostModal(character, title=f"{character.name}'s Post", **kwargs)
        await ctx.send_modal(modal)

    except inconnu.errors.CharacterNotFoundError as err:
        await inconnu.utils.error(ctx, err, help_url=__HELP_URL)


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
