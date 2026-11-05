"""experience/bulk.py - Bulk award XP."""

import re
from typing import Any, cast

import discord
from discord.ext.commands import Paginator
from discord.ui import InputText, Modal
from loguru import logger
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import PyMongoError

import db
import errors
import services
import ui
from ctx import AppCtx, AppInteraction


async def bulk_award_xp(ctx: AppCtx):
    """Present a modal for bulk-awarding XP."""
    modal = _BulkModal(title="Bulk Award XP")
    await ctx.send_modal(modal)


class _BulkModal(Modal):
    """A modal for entering XP awards."""

    def __init__(self, *args: Any, **kwargs: Any):
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
                label="Reason",
                placeholder="Enter the reason for the XP award.",
                required=True,
                max_length=200,
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
        inter = cast(AppInteraction, interaction)
        guild = cast(discord.Guild, inter.guild)  # The command is guild-only
        await inter.response.defer()
        reason = (self.children[0].value or "").strip()
        if not reason:
            await ui.embeds.error(inter, "The reason can't be blank.")
            return

        entries = (self.children[1].value or "").split("\n")
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

            member = guild.get_member(owner)
            member = member.mention if member is not None else owner

            if experience == 0:
                self.errors.append(f"**Zero XP:** {member}: `{char_name}`")
                continue

            try:
                character = await services.char_mgr.fetchone(guild, owner, char_name)

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
                        (character, [experience, "lifetime", reason, inter.user.id])
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
            await ui.embeds.error(interaction, "You didn't supply any input!")

    async def _present_errors(self, interaction: discord.Interaction):
        """Show the error message. No XP awarded."""
        contents = "**NO XP HAS BEEN AWARDED!** Correct the errors below and try again."
        self._chunk_fields()

        fields = [("Would Award", page) for page in self.would_award] if self.would_award else []
        fields.extend([("Errors", page) for page in self.errors])

        await ui.embeds.error(interaction, contents, *fields, ephemeral=False)

    async def _award_xp(self, interaction: discord.Interaction):
        """Award the XP. Every character is saved, or none is."""
        self._chunk_fields()

        embed = discord.Embed(title="Bulk Awarding XP", color=0x7ED321)
        for page in self.would_award:
            embed.add_field(name="Awarding", value=page, inline=False)

        characters = [character for character, _ in self.xp_tasks]
        originals = [character.experience.model_copy(deep=True) for character in characters]
        for character, xp_args in self.xp_tasks:
            character.apply_experience(*xp_args)

        try:
            await db.transaction(self._save_all)
        except Exception as err:
            # Nothing was saved, so undo the cached changes too. Beanie's
            # rollback() can't: save() marks the XP as saved even when the
            # transaction is then aborted.
            for character, experience in zip(characters, originals):
                character.experience = experience
            if not isinstance(err, PyMongoError):
                raise

            logger.exception("Bulk XP award failed")
            await ui.embeds.error(
                interaction, "Couldn't save the awards, so no XP was awarded. Please try again."
            )
            return

        await interaction.followup.send(embed=embed)

    async def _save_all(self, session: AsyncClientSession):
        """Save the awarded characters in the transaction. Retries save them
        again, which is harmless."""
        for character, _ in self.xp_tasks:
            await character.save(session=session)

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
