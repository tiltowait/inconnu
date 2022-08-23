"""Full-size character image display."""

from typing import Optional

import discord

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
        allow_lookups=True,
        errmsg="None of your characters have any images! Upload via `/character image upload`.",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    pager = ImagePager(ctx, character, haven.owner)
    await pager.respond()


def _has_image(character):
    """Raises an error if the character doesn't have an image."""
    for image in character.profile.images:
        # We need to make sure the image isn't an empty string.
        if image:
            return
    raise inconnu.errors.CharacterError(
        f"{character.name} doesn't have any images! Upload via `/character image upload`."
    )


class ImagePager(ReportingView):
    """
    A display that pages through character images. It features two modes: view
    and manage. In management mode, the character's owner may delete or promote
    images. Management mode is only available if the initiating user is the
    character's owner.
    """

    def __init__(self, ctx, character, owner):
        self.ctx = ctx
        self.message = None
        self.character = character
        self.owner = owner
        self.current_page = 0
        self.management_mode = False

        # Standard paging buttons
        self.first_button = discord.ui.Button(
            label="<<", style=discord.ButtonStyle.primary, disabled=True
        )
        self.first_button.callback = self.first_page
        self.prev_button = discord.ui.Button(label="<", style=discord.ButtonStyle.danger)
        self.prev_button.callback = self.previous_page
        self.indicator = discord.ui.Button(label=self.indicator_label, disabled=True)
        self.next_button = discord.ui.Button(label=">", style=discord.ButtonStyle.success)
        self.next_button.callback = self.next_page
        self.last_button = discord.ui.Button(label=">>", style=discord.ButtonStyle.primary)
        self.last_button.callback = self.last_page

        self.manage_button = discord.ui.Button(label="Manage", row=1)
        self.manage_button.callback = self.mode_toggle

        # Management mode buttons
        self.delete_button = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger)
        self.delete_button.callback = self._delete_image
        self.promote_button = discord.ui.Button(label="Promote", style=discord.ButtonStyle.primary)
        self.cancel_button = discord.ui.Button(label="Cancel", row=1)
        self.cancel_button.callback = self.mode_toggle

        super().__init__(timeout=300)
        self.add_pager_buttons()

    @property
    def num_pages(self) -> int:
        """The number of pages in the view."""
        return len(self.character.profile.images)

    @property
    def indicator_label(self) -> str:
        """The label for the page indicator."""
        return f"{self.current_page + 1}/{self.num_pages}"

    @property
    def current_image(self) -> str:
        """The URL of the current image."""
        return self.character.profile.images[self.current_page]

    def add_pager_buttons(self):
        """Add the pager buttons."""
        if self.num_pages > 1:
            self.add_item(self.first_button)
            self.add_item(self.prev_button)
            self.add_item(self.indicator)
            self.add_item(self.next_button)
            self.add_item(self.last_button)

        if self.character.user == self.ctx.user.id:
            self.add_item(self.manage_button)

    def remove_all_items(self):
        """Remove all buttons."""
        children = list(self.children)
        for child in children:
            self.remove_item(child)

    async def respond(self):
        """Display the pager."""
        embed = inconnu.utils.VCharEmbed(self.ctx, self.character, self.owner, show_thumbnail=False)
        embed.set_footer(text="Upload some with /character image upload.")
        embed.set_image(url=self.current_image)

        self.message = await self.ctx.respond(embed=embed, view=self)

    async def previous_page(self, interaction: discord.Interaction):
        """Go to the next page."""
        if self.current_page == 0:
            await self.goto_page(self.num_pages - 1, interaction)
        else:
            await self.goto_page(self.current_page - 1, interaction)

    async def next_page(self, interaction: discord.Interaction):
        """Go to the next page."""
        if self.current_page >= self.num_pages - 1:
            await self.goto_page(0, interaction)
        else:
            await self.goto_page(self.current_page + 1, interaction)

    async def first_page(self, interaction: discord.Interaction):
        """Go to the first page."""
        await self.goto_page(0, interaction)

    async def last_page(self, interaction: discord.Interaction):
        """Go to the last page."""
        await self.goto_page(self.num_pages - 1, interaction)

    async def goto_page(self, page_number: int, interaction: discord.Interaction):
        """Go to a specific page number."""
        if not self.num_pages:
            await self._display_no_images(interaction)
            return

        self.current_page = page_number
        self.indicator.label = self.indicator_label

        self.first_button.disabled = self.current_page == 0
        self.last_button.disabled = self.current_page == self.num_pages - 1

        embed = interaction.message.embeds[0]
        embed.set_image(url=self.current_image)
        await interaction.response.edit_message(embed=embed, view=self)

    async def _display_no_images(self, interaction: discord.Interaction):
        """Inform the character has no images if the last image is deleted."""
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

    async def mode_toggle(self, interaction: discord.Interaction):
        """Toggle between management and normal modes."""
        if self.management_mode:
            self.remove_all_items()
            self.add_pager_buttons()
        else:
            self.remove_all_items()
            self.add_item(self.delete_button)
            # self.add_item(self.promote_button)
            self.add_item(self.cancel_button)

        self.management_mode = not self.management_mode
        await interaction.response.edit_message(view=self)

    # Image manipulation

    async def _delete_image(self, interaction: discord.Interaction):
        """Delete the current image."""
        image_url = self.character.profile.images.pop(self.current_page)
        Logger.info("IMAGES: Removing %s from %s", image_url, self.character.name)

        if self.num_pages == 0:
            Logger.debug("IMAGES: Deleted %s's last image", self.character.name)
            await self._display_no_images(interaction)
        else:
            page = min(self.current_page, self.num_pages - 1)
            await self.goto_page(page, interaction)

        if s3.is_managed_url(image_url):
            await s3.delete_file(image_url)
            await inconnu.db.upload_log.update_one({"url": image_url}, {"$set": {"deleted": True}})
        await self.character.commit()

    async def interaction_check(self, interaction: discord.Interaction):
        """Ensure image management safety."""
        if interaction.user.id == self.character.user:
            return True
        if self.management_mode or self.manage_button.custom_id == interaction.data["custom_id"]:
            await interaction.response.send_message(
                "You may only manage your own characters' images.", ephemeral=True
            )
            return False

        return True

    async def on_timeout(self):
        """Delete the components."""
        if self.children:
            Logger.debug("IMAGES: View timed out; deleting components")
            await self.message.edit_original_message(view=None)
        else:
            Logger.debug("IMAGES: View timed out, but no components")
