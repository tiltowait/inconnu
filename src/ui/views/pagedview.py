"""views/pagedview.py - A components v2 paginator."""

from collections.abc import Sequence
from typing import Self

import discord
from discord.ui import ActionRow, Button, ViewItem

from ctx import AppInteraction


class PagedView(discord.ui.DesignerView):
    """A paginated display. Each page is a list of top-level items, such as
    containers or text displays. Page controls show only if there are several
    pages. If given an author, only they may turn pages."""

    def __init__(
        self,
        pages: Sequence[Sequence[ViewItem]],
        *,
        author: discord.abc.User | None = None,
        timeout: float = 300,
    ):
        if not pages:
            raise ValueError("PagedView needs at least one page")

        # A single page has no controls to disable
        super().__init__(timeout=timeout, disable_on_timeout=len(pages) > 1)
        self.pages = pages
        self.author = author
        self.current = 0

        self.prev_button = Button(emoji="◀️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_page
        self.page_button = Button(style=discord.ButtonStyle.secondary, disabled=True)
        self.next_button = Button(emoji="▶️", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page

        self._render()

    def _render(self):
        """Show the current page and, if there are several, the page controls."""
        self.clear_items()
        for item in self.pages[self.current]:
            self.add_item(item)

        if len(self.pages) > 1:
            self.prev_button.disabled = self.current == 0
            self.next_button.disabled = self.current == len(self.pages) - 1
            self.page_button.label = f"{self.current + 1}/{len(self.pages)}"
            self.add_item(ActionRow(self.prev_button, self.page_button, self.next_button))

    def disable_all_items(self, *, exclusions: list[ViewItem] | None = None) -> Self:
        """Disable the page controls. The page content, such as link buttons,
        stays usable."""
        controls = (self.prev_button, self.page_button, self.next_button)
        content = [item for item in self.walk_children() if item not in controls]
        return super().disable_all_items(exclusions=content + (exclusions or []))

    async def _turn(self, interaction: discord.Interaction, offset: int):
        """Move by the offset and redraw."""
        self.current = max(0, min(self.current + offset, len(self.pages) - 1))
        self._render()
        await interaction.edit(view=self)

        # On timeout, ephemeral messages are edited through self.parent, whose
        # token expires after 15 minutes. The latest press's token is fresher.
        self.parent = interaction

    async def prev_page(self, interaction: discord.Interaction):
        """Go to the previous page."""
        await self._turn(interaction, -1)

    async def next_page(self, interaction: discord.Interaction):
        """Go to the next page."""
        await self._turn(interaction, 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Restrict page turns to the author, if there is one."""
        if self.author is None or interaction.user is None:
            return self.author is None
        return interaction.user.id == self.author.id

    async def on_check_failure(self, interaction: discord.Interaction):
        """Tell others they can't turn the pages."""
        await interaction.respond("These pages aren't yours to turn.", ephemeral=True)

    async def on_error(self, error, _, interaction: AppInteraction):  # type:ignore
        """Report an error using Reporter functionality."""
        # Inline to avoid a circular import (services.reporter imports ui)
        from services.reporter import reporter

        await reporter.report_error(interaction, error)
