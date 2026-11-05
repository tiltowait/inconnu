"""experience/remove.py - Remove an XP log entry."""

from typing import cast

import discord

import services
import ui
from ctx import AppCtx, AppInteraction
from inconnu.character.display import DisplayField, display
from models import VChar
from models.vchardocs import VCharExperienceEntry
from services.haven import haven
from ui.views import DisablingView
from utils import get_avatar, get_message
from utils.permissions import is_admin
from utils.urls import docs_url

__HELP_URL = docs_url("advanced/administration/experience-management")


@haven(__HELP_URL)
async def remove_entry(
    ctx: AppCtx,
    character: VChar,
    index: int,
    *,
    player: discord.Member,
):
    """Remove an entry from a character's experience log."""
    try:
        # Log entries are presented to the user in reverse, so we need the
        # negative index
        entry_to_delete = character.experience.log.pop(-index)
        await character.save()  # Before responding, so a failed response can't hide the change

        embed = _get_embed(player, character, entry_to_delete)
        view = _ExperienceView(character, player, entry_to_delete)
        await ctx.respond(embed=embed, view=view)

    except IndexError:
        err = f"{character.name} has no experience log entry at index `{index}`."
        await ui.embeds.error(ctx, err)


def _get_embed(player: discord.Member, character: VChar, entry: VCharExperienceEntry):
    """Generate an embed for displaying the deletion message."""
    embed = discord.Embed(title="Deleted Experience Log Entry", description=_format_entry(entry))
    embed.set_author(name=character.name, icon_url=get_avatar(player))
    embed.set_footer(text="Be sure to adjust unspent/lifetime XP accordingly!")

    experience = f"```{character.experience.unspent} / {character.experience.lifetime}```"
    embed.add_field(name="Experience", value=experience)

    return embed


def _format_entry(entry: VCharExperienceEntry):
    """Format the deleted entry for display."""
    date = entry.date.strftime("%b %d, %Y")
    scope = _entry_scope(entry)

    return f"**{entry.amount:+} {scope} XP: {entry.reason}** *({date})*"


def _entry_scope(entry: VCharExperienceEntry):
    """Get the log entry scope."""
    return entry.event.split("_")[-1].capitalize()


class _ExperienceView(DisablingView):
    """A View that adds or deducts the proper XP from a character when pressed."""

    def __init__(self, character: VChar, player: discord.Member, entry: VCharExperienceEntry):
        super().__init__()

        self.character = character
        self.player = player
        self.scope = _entry_scope(entry)
        self.amount = entry.amount * -1

        if self.amount < 0:
            title = f"Remove {abs(self.amount)} {self.scope} XP"
        else:
            title = f"Add {abs(self.amount)} {self.scope} XP"

        button = discord.ui.Button(label=title, style=discord.ButtonStyle.primary)
        button.callback = self.apply_xp
        self.add_item(button)

    async def apply_xp(self, interaction: discord.Interaction):
        """Apply the XP to the character."""
        inter = cast(AppInteraction, interaction)
        experience = self.character.experience
        if self.scope == "Unspent":
            experience.unspent += self.amount
            message = f"* `{self.amount:+}` unspent XP."
        else:
            unspent, lifetime = experience.unspent, experience.lifetime
            self.character.set_lifetime_xp(lifetime + self.amount)
            message = (
                f"* `{experience.unspent - unspent:+}` unspent XP.\n"
                f"* `{experience.lifetime - lifetime:+}` lifetime XP."
            )

        await inter.response.edit_message(view=None)

        field = DisplayField.EXPERIENCE
        msg = await display(
            inter,
            self.character,
            fields=[(field.value, field)],
            owner=self.player,
            message=message,
        )
        await self.character.save()

        user = inter.user
        await services.post_update(
            ctx=inter,
            msg=await get_message(msg),
            character=self.character,
            title="Character Updated",
            message=f"__{user.mention} updated {self.character.name}:__\n" + message,
        )
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check whether the user is an admin."""
        if not is_admin(interaction.user):
            await interaction.response.send_message("Only an admin can do this.", ephemeral=True)
            return False

        return True
