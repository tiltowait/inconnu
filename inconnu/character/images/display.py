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
        errmsg="None of your characters have any images! Upload via `/character image upload`.",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    paginator = ImagePaginator(ctx, character, haven.owner)
    await paginator.respond(ctx.interaction)


def _has_image(character):
    """Raises an error if the character doesn't have an image."""
    for image in character.image_urls:
        # We need to make sure the image isn't an empty string.
        if image:
            return
    raise inconnu.errors.CharacterError(
        f"{character.name} doesn't have any images! Upload via `/character image upload`."
    )


class ImagePaginator(pages.Paginator):
    """A Paginator for displaying character images."""

    def __init__(self, ctx, character, owner):
        self.ctx = ctx
        self.character = character
        self.owner = owner
        self.embeds = self._generate_pages()

        super().__init__(
            self.embeds,
            loop_pages=True,
            author_check=False,
            custom_view=_DeleteImageView(character.user, self._delete_image),
        )

    async def _delete_image(self, interaction: discord.Interaction):
        """Delete the image."""
        del self.embeds[self.current_page]
        image_url = self.character.image_urls[self.current_page]
        Logger.info("IMAGES: Removing %s from %s", image_url, self.character.name)

        if self.embeds:
            await self.update(
                pages=self.embeds,
                loop_pages=True,
                author_check=False,
                custom_view=self.custom_view,
                interaction=interaction,
            )
        else:
            embed = inconnu.utils.VCharEmbed(
                self.ctx,
                self.character,
                self.owner,
                title="No Images",
                description=f"**{self.character.name}** has no images!",
                show_thumbnail=False,
            )
            embed.set_footer(text="Upload some with /character image upload.")

            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            self.custom_view.stop()

        # Now that we've updated the display, do the actual work of removing
        # the images from both S3 and the VChar object. Since the image might
        # be an unmanaged URL, we modify the character outside of the if
        # statement.
        await self.character.remove_image_url(self.current_page)

        if s3.is_managed_url(image_url):
            await s3.delete_file(image_url)

    def _generate_pages(self):
        """Generate the pages."""
        pages_ = []
        for image in self.character.image_urls:
            Logger.debug("IMAGES: (%s) Making view for %s", self.character.name, image)
            embed = inconnu.utils.VCharEmbed(
                self.ctx, self.character, self.owner, show_thumbnail=False
            )
            embed.set_image(url=image)
            embed.set_footer(
                text=(
                    "Images are a premium feature. Become a supporter with /patreon!\n"
                    "Users are solely responsible for image content."
                )
            )
            pages_.append(embed)

        Logger.info("IMAGES: Found %s images for %s", len(pages_), self.character.name)
        return pages_


class _DeleteImageView(ReportingView):
    """A View that tells its parent to delete images."""

    def __init__(self, owner, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.callback = callback

    @discord.ui.button(label="Delete Image", style=discord.ButtonStyle.danger)
    async def delete_image(self, _, interaction: discord.Interaction):
        """Inform the callback of the deletion event."""
        if interaction.user.id != self.owner:
            await interaction.response.send_message(
                "This character doesn't belong to you!",
                ephemeral=True,
            )
        else:
            await self.callback(interaction)
