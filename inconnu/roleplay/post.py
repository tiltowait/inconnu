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
        self.mention = kwargs.pop("mention")

        header_params = {
            param: kwargs.pop(param, None)
            for param in ["blush", "location", "merits", "flaws", "temp", "hunger"]
        }
        self.header = inconnu.models.HeaderSubdoc.create(character, **header_params)

        # We create a throwaway embed to determine the max possible post length
        embed = inconnu.header.embed(self.header, self.character)
        header_len = len(embed.description)

        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Post details",
                placeholder="Your RP post",
                min_length=1,
                max_length=4000 - header_len - len(self.DIVIDER),  # 33 is from the divider
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Set the RP post content."""
        lines = self.children[0].value.split("\n")
        cleaned = [inconnu.utils.clean_text(line) for line in lines if line]
        content = "\n\n".join(cleaned)

        # We will use a basic RP header as the base for our embed
        rp_post = inconnu.header.embed(self.header, self.character)
        rp_post.description += self.DIVIDER + content

        if self.mention:
            resp = await interaction.response.send_message(self.mention.mention, embed=rp_post)
        else:
            resp = await interaction.response.send_message(embed=rp_post)

        # Register the header
        message = await resp.original_response()
        await inconnu.header.register(interaction, message, self.character)
        Logger.info("POST: %s registered header", self.character.name)

        # Register the RP post
        db_rp_post = inconnu.models.RPPost.create(
            self.character, self.header, content, message.jump_url
        )
        await db_rp_post.commit()
        Logger.info("POST: %s registered post", self.character.name)


async def post(ctx: discord.ApplicationContext, character: str, **kwargs):
    """Create a modal that sends an RP post."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = PostModal(character, title=f"{character.name}'s Post", **kwargs)
        await ctx.send_modal(modal)

    except inconnu.errors.CharacterNotFoundError as err:
        await inconnu.utils.error(ctx, err, help_url=__HELP_URL)
