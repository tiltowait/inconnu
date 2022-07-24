"""Full-size character image display."""

from typing import Optional

import discord
from discord.ext import pages

import inconnu
import s3
from logger import Logger

from ...views import ReportingView

__HELP_URL = "https://www.inconnu.app"


async def display_images(
    ctx: discord.ApplicationContext,
    character: Optional[str],
    player: Optional[discord.Member],
):
    """Display a character's images inside a paginator."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        owner=player,
        tip="`/character images` `character:CHARACTER` `player:PLAYER`",
        char_filter=_has_image,
        errmsg="None of your characters have any images!",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    pages_ = []
    for image in character.image_urls:
        embed = inconnu.utils.VCharEmbed(ctx, character, haven.owner, show_thumbnail=False)
        embed.set_thumbnail(url=ctx.guild.icon)
        embed.set_image(url=image)
        embed.set_footer(
            text=(
                "Images are a premium feature. Become a supporter with /patreon!\n"
                "Users are solely responsible for image content."
            )
        )
        pages_.append(
            pages.Page(
                embeds=[embed],
                custom_view=_DeleteImageView(character, image),
            )
        )

    paginator = pages.Paginator(pages_, loop_pages=True)
    await paginator.respond(ctx.interaction)


def _has_image(character):
    """Raises an error if the character doesn't have an image."""
    for image in character.image_urls:
        if image:
            return
    raise inconnu.errors.CharacterError(f"{character.name} has no images set!")


class _DeleteImageView(ReportingView):
    """A view for deleting character images."""

    def __init__(self, character, image_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character
        self.image_url = image_url

        if not image_url.startswith(s3.BASE_URL):
            Logger.debug("IMAGES: %s is not an S3 URL", image_url)
            self.disable_all_items()

    @discord.ui.button(label="Delete Image", style=discord.ButtonStyle.danger)
    async def delete_image(self, _, interaction: discord.Interaction):
        """Delete the image."""
        object_name = self.image_url.replace(s3.BASE_URL, "")
        Logger.info("IMAGES: Deleting %s", object_name)

        # We don't have the paginator object to modify its contents, so let's
        # just edit the embed instead.
        embed = interaction.message.embeds[0]
        embed.set_image(url="")
        embed.description = "**Image deleted.** Run `/character images` again to refresh!"
        embed.set_footer(text=discord.Embed.Empty)
        await interaction.response.edit_message(embed=embed, view=None)

    async def interaction_check(self, interaction: discord.Interaction):
        """Ensure only the character's owner can click the button."""
        if self.character.user != interaction.user.id:
            await interaction.response.send_message("You don't own this button!", ephemeral=True)
            return False
        return True
