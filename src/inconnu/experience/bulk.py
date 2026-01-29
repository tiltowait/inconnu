"""experience/bulk.py - Bulk award XP."""

import asyncio
import re

import discord
from discord.ext.commands import Paginator
from discord.ui import InputText, Modal

import errors
import inconnu


async def bulk_award_xp(ctx):
    """Present a modal for bulk-awarding XP."""
    modal = _BulkModal(title="Bulk Award XP")
    await ctx.send_modal(modal)


class _BulkModal(Modal):
    """A modal for entering XP awards."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pattern = re.compile(r"^(?P<xp>\d+)\s*xp\s*<@!?(?P<user>\d+)> (?P<character>.*)$")
        self.xp_tasks = []
        self.would_award = []
        self.errors = []

        instructions = (
            "N xp <@User ID> Character Name\n"
            "3 xp <@127623457834687236> Jimmy Maxwell\n"
            "(One entry per line)"
        )

        self.add_item(
            InputText(
                label="Reason", placeholder="Enter the reason for the XP award.", required=True
            )
        )
        self.add_item(
            InputText(
                label="Experience List",
                placeholder=instructions,
                style=discord.InputTextStyle.long,
                required=True,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Find the characters and apply their XP."""
        await interaction.response.defer()
        reason = self.children[0].value.strip()
        entries = self.children[1].value.split("\n")
        seen = set()  # For making sure duplicates aren't made

        # Set up the containers

        for entry in entries:
            entry = " ".join(entry.split())  # Normalize
            if not entry:
                # Ignore empty lines
                continue
            if (match := self.pattern.match(entry)) is None:
                self.errors.append(f"**Invalid syntax:** {entry}")
                continue

            # We found the match
            experience = int(match.group("xp"))
            owner = int(match.group("user"))
            char_name = match.group("character")

            member = interaction.guild.get_member(owner)
            member = member.mention if member is not None else owner

            try:
                character = await inconnu.char_mgr.fetchone(interaction.guild, owner, char_name)

                # Make sure this isn't a duplicate award
                match = f"{member} {character.name}"
                if match in seen:
                    self.errors.append(f"**Duplicate:** {member}: `{char_name}` ({experience}xp)")
                else:
                    # We need bulk awarding to be multi-document atomic. To
                    # accomplish this, we store the character and the
                    # experience arguments in a list of tuples. If we receive
                    # no errors, then we will commit them all at once.
                    self.xp_tasks.append(
                        (character, [experience, "lifetime", reason, interaction.user.id])
                    )
                    self.would_award.append(f"`{experience}xp`: `{character.name}` {member}")

                    # Prevent the character from being awarded again
                    seen.add(match)

            except errors.CharacterNotFoundError:
                self.errors.append(f"**Not found:** {member}: `{char_name}`")

        # Finished parsing input
        if self.errors:
            await self._present_errors(interaction)
        elif self.xp_tasks:
            await self._award_xp(interaction)
        else:
            await inconnu.embeds.error(interaction, "You didn't supply any input!")

    async def _present_errors(self, interaction):
        """Show the error message. No XP awarded."""
        contents = "**NO XP HAS BEEN AWARDED!** Correct the errors below and try again."
        self._chunk_fields()

        fields = [("Would Award", page) for page in self.would_award] if self.would_award else []
        fields.extend([("Errors", page) for page in self.errors])

        await inconnu.embeds.error(interaction, contents, *fields, ephemeral=False)

    async def _award_xp(self, interaction):
        """Award the XP."""
        self._chunk_fields()

        embed = discord.Embed(title="Bulk Awarding XP", color=0x7ED321)
        for page in self.would_award:
            embed.add_field(name="Awarding", value=page, inline=False)

        commit_tasks = []
        for character, xp_args in self.xp_tasks:
            character.apply_experience(*xp_args)
            commit_tasks.append(character.save())

        send_embed = interaction.followup.send(embed=embed)
        await asyncio.gather(*commit_tasks, send_embed)

    def _chunk_fields(self):
        """Split the fields up into smaller chunks."""
        size = 1024

        paginator = Paginator(max_size=size, suffix="", prefix="")

        for line in self.would_award:
            paginator.add_line(line)

        self.would_award = paginator.pages

        paginator = Paginator(max_size=size, suffix="", prefix="")

        for line in self.errors:
            paginator.add_line(line)

        self.errors = paginator.pages
