"""experience/bulk.py - Bulk award XP."""

import asyncio
import re

import discord
from discord.ui import InputText, Modal

import inconnu


async def bulk_award_xp(ctx):
    """Present a modal for bulk-awarding XP."""
    modal = _BulkModal(title="Bulk Award XP")
    await ctx.send_modal(modal)


class _BulkModal(Modal):
    """A modal for entering XP awards."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pattern = re.compile(r"^(?P<xp>\d+) xp <@!?(?P<user>\d+)> (?P<character>.*)$")
        self.xp_tasks = []
        self.would_award = []
        self.errors = []

        instructions = "One entry per line. Format: N xp <@!USER_ID> CHAR_NAME"
        instructions += "\n\nExample:\n\n5 xp <@!229736753676681230> Nadea"

        self.add_item(
            InputText(
                label="Reason",
                placeholder="Enter the reason for the XP award.",
                required=True
            )
        )
        self.add_item(
            InputText(
                label="Experience List",
                placeholder=instructions,
                style=discord.InputTextStyle.long,
                required=True
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Find the characters and apply their XP."""
        await interaction.response.defer()
        reason = self.children[0].value.strip()
        entries = self.children[1].value.split("\n")

        # Set up the containers

        for entry in entries:
            entry = " ".join(entry.split()) # Normalize
            if not entry:
                # Ignore empty lines
                continue
            if (match := self.pattern.match(entry)) is None:
                self.errors.append(f"Invalid syntax: {entry}")
                continue

            # We found the match
            experience = int(match.group("xp"))
            owner = int(match.group("user"))
            char_name = match.group("character")

            member = interaction.guild.get_member(owner)
            member = member.mention if member is not None else owner

            try:
                character = await inconnu.char_mgr.fetchone(interaction.guild, owner, char_name)
                self.xp_tasks.append(
                    character.apply_experience(experience, "lifetime", reason, interaction.user.id)
                )
                self.would_award.append(f"`{experience}xp`: `{character.name}` {member}")

            except inconnu.vchar.errors.CharacterNotFoundError:
                self.errors.append(f"**Not found:** {member}: `{char_name}`")

        # Finished finding characters
        if self.errors:
            await self._present_errors(interaction)
        elif self.xp_tasks:
            await self._award_xp(interaction)
        else:
            await inconnu.common.present_error(interaction, "You didn't supply any input!")


    async def _present_errors(self, interaction):
        """Show the error message. No XP awarded."""
        contents = "**NO XP HAS BEEN AWARDED!** Correct the errors below and try again."
        fields = [("Would Award", "\n".join(self.would_award))] if self.would_award else []
        fields.append(("Errors", "\n".join(self.errors)))

        await inconnu.common.present_error(interaction, contents, *fields, ephemeral=False)


    async def _award_xp(self, interaction):
        """Award the XP."""
        await interaction.followup.send("**Awarding:**\n" + "\n".join(self.would_award))
        await asyncio.gather(*self.xp_tasks)
